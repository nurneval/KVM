#!/usr/bin/env python  
# _#_ coding:utf-8 _*_  
import libvirt,time,os,threading,socket
from datetime import datetime
from xml.dom import minidom
from xml.etree import ElementTree
from VManagePlatform.apps.Base import BaseLogging
from VManagePlatform.const import Const
from VManagePlatform.utils.vConnUtils import CommTools,TokenUntils
from VManagePlatform.utils import vMUtil
from libvirt import libvirtError
from VManagePlatform.utils.rwlock import ReadWriteLock
from django.conf import settings

CONN_SOCKET = 4
CONN_TLS = 3
CONN_SSH = 2
CONN_TCP = 1
TLS_PORT = 16514
SSH_PORT = 22
TCP_PORT = 16509


class soloConnection(object):

    def __init__(self, host, login=None, passwd=None, conn=1):
        self.connection = None
        self.last_error = None
        self.host = host
        self.login = login
        self.passwd = passwd
        self.type = conn
        
    def connect(self):
        if self.type == CONN_TCP:
            self.connection = self.__connect_tcp()
        elif self.type == CONN_SSH:
            self.connection = self.__connect_ssh()
        elif self.type == CONN_TLS:
            self.connection = self.__connect_tls()
        elif self.type == CONN_SOCKET:
            self.connection = self.__connect_socket()
        else:
            raise ValueError('"{type}" is not a valid connection type'.format(type=self.type))
        return self.connection

    def __libvirt_auth_credentials_callback(self, credentials, user_data):
        for credential in credentials:
            if credential[0] == libvirt.VIR_CRED_AUTHNAME:
                credential[4] = self.login
                if len(credential[4]) == 0:
                    credential[4] = credential[3]
            elif credential[0] == libvirt.VIR_CRED_PASSPHRASE:
                credential[4] = self.passwd
            else:
                return -1
        return 0



    def __connect_tcp(self):
        flags = [libvirt.VIR_CRED_AUTHNAME, libvirt.VIR_CRED_PASSPHRASE]
        auth = [flags, self.__libvirt_auth_credentials_callback, None]
        uri = 'qemu+tcp://%s/system' % self.host

        try:
            return libvirt.openAuth(uri, auth, 0)
        except libvirtError as e:
            self.last_error = 'Connection Failed: ' + str(e)
            self.connection = None

    def __connect_ssh(self):
        uri = 'qemu+ssh://%s@%s/system' % (self.login, self.host)

        try:
            return libvirt.open(uri)
        except libvirtError as e:
            self.last_error = 'Connection Failed: ' + str(e) + ' --- ' + repr(libvirt.virGetLastError())
            self.connection = None

    def __connect_tls(self):
        flags = [libvirt.VIR_CRED_AUTHNAME, libvirt.VIR_CRED_PASSPHRASE]
        auth = [flags, self.__libvirt_auth_credentials_callback, None]
        uri = 'qemu+tls://%s@%s/system' % (self.login, self.host)

        try:
            return libvirt.openAuth(uri, auth, 0)
        except libvirtError as e:
            self.last_error = 'Connection Failed: ' + str(e)
            self.connection = None

    def __connect_socket(self):
        uri = 'qemu:///system'

        try:
            return libvirt.open(uri)
        except libvirtError as e:
            self.last_error = 'Connection Failed: ' + str(e)
            self.connection = None

    def close(self):
        try:
            self.connection.close()
        except libvirtError:
            pass


class wvmEventLoop(threading.Thread):
    def __init__(self, group=None, target=None, name=None, args=(), kwargs={}):
        libvirt.virEventRegisterDefaultImpl()

        if name is None:
            name = 'libvirt event loop'

        super(wvmEventLoop, self).__init__(group, target, name, args, kwargs)
        self.daemon = True

    def run(self):
        while True:
            libvirt.virEventRunDefaultImpl()


class wvmConnection(object):

    def __init__(self, host, login, passwd, conn):
        self.connection_state_lock = threading.Lock()
        self.connection = None
        self.last_error = None
        self.host = host
        self.login = login
        self.passwd = passwd
        self.type = conn
        self.connect()

    def connect(self):
        self.connection_state_lock.acquire()
        try:
            if not self.connected:
                if self.type == CONN_TCP:
                    self.__connect_tcp()
                elif self.type == CONN_SSH:
                    self.__connect_ssh()
                elif self.type == CONN_TLS:
                    self.__connect_tls()
                elif self.type == CONN_SOCKET:
                    self.__connect_socket()
                else:
                    raise ValueError('"{type}" is not a valid connection type'.format(type=self.type))

                if self.connected:
                    try:
                        self.connection.setKeepAlive(connection_manager.keepalive_interval, connection_manager.keepalive_count)
                        try:
                            self.connection.registerCloseCallback(self.__connection_close_callback, None)
                        except:
                            pass
                    except libvirtError as e:
                        self.last_error = str(e)
        finally:
            self.connection_state_lock.release()

    @property
    def connected(self):
        try:
            return self.connection is not None and self.connection.isAlive()
        except libvirtError:
            return False

    def __libvirt_auth_credentials_callback(self, credentials, user_data):
        for credential in credentials:
            if credential[0] == libvirt.VIR_CRED_AUTHNAME:
                credential[4] = self.login
                if len(credential[4]) == 0:
                    credential[4] = credential[3]
            elif credential[0] == libvirt.VIR_CRED_PASSPHRASE:
                credential[4] = self.passwd
            else:
                return -1
        return 0

    def __connection_close_callback(self, connection, reason, opaque=None):
        self.connection_state_lock.acquire()
        try:
            if libvirt is not None:
                if (reason == libvirt.VIR_CONNECT_CLOSE_REASON_ERROR):
                    self.last_error = 'connection closed: Misc I/O error'
                elif (reason == libvirt.VIR_CONNECT_CLOSE_REASON_EOF):
                    self.last_error = 'connection closed: End-of-file from server'
                elif (reason == libvirt.VIR_CONNECT_CLOSE_REASON_KEEPALIVE):
                    self.last_error = 'connection closed: Keepalive timer triggered'
                elif (reason == libvirt.VIR_CONNECT_CLOSE_REASON_CLIENT):
                    self.last_error = 'connection closed: Client requested it'
                else:
                    self.last_error = 'connection closed: Unknown error'
            self.connection = None
        finally:
            self.connection_state_lock.release()

    def __connect_tcp(self):
        flags = [libvirt.VIR_CRED_AUTHNAME, libvirt.VIR_CRED_PASSPHRASE]
        auth = [flags, self.__libvirt_auth_credentials_callback, None]
        uri = 'qemu+tcp://%s/system' % self.host

        try:
            self.connection = libvirt.openAuth(uri, auth, 0)
            self.last_error = None

        except libvirtError as e:
            self.last_error = 'Connection Failed: ' + str(e)
            self.connection = None

    def __connect_ssh(self):
        uri = 'qemu+ssh://%s@%s/system' % (self.login, self.host)

        try:
            self.connection = libvirt.open(uri)
            self.last_error = None

        except libvirtError as e:
            self.last_error = 'Connection Failed: ' + str(e) + ' --- ' + repr(libvirt.virGetLastError())
            self.connection = None

    def __connect_tls(self):
        flags = [libvirt.VIR_CRED_AUTHNAME, libvirt.VIR_CRED_PASSPHRASE]
        auth = [flags, self.__libvirt_auth_credentials_callback, None]
        uri = 'qemu+tls://%s@%s/system' % (self.login, self.host)

        try:
            self.connection = libvirt.openAuth(uri, auth, 0)
            self.last_error = None

        except libvirtError as e:
            self.last_error = 'Connection Failed: ' + str(e)
            self.connection = None

    def __connect_socket(self):
        uri = 'qemu:///system'

        try:
            self.connection = libvirt.open(uri)
            self.last_error = None

        except libvirtError as e:
            self.last_error = 'Connection Failed: ' + str(e)
            self.connection = None

    def close(self):
        self.connection_state_lock.acquire()
        try:
            if self.connected:
                try:
                    # to-do: handle errors?
                    self.connection.close()
                except libvirtError:
                    pass

            self.connection = None
            self.last_error = None
        finally:
            self.connection_state_lock.release()

    def __del__(self):
        if self.connection is not None:
            try:
                self.connection.unregisterCloseCallback()
            except:
                pass

    def __unicode__(self):
        if self.type == CONN_TCP:
            type_str = u'tcp'
        elif self.type == CONN_SSH:
            type_str = u'ssh'
        elif self.type == CONN_TLS:
            type_str = u'tls'
        else:
            type_str = u'invalid_type'

        return u'qemu+{type}://{user}@{host}/system'.format(type=type_str, user=self.login, host=self.host)

    def __repr__(self):
        return '<wvmConnection {connection_str}>'.format(connection_str=unicode(self))


class wvmConnectionManager(object):
    def __init__(self, keepalive_interval=5, keepalive_count=5):
        self.keepalive_interval = keepalive_interval
        self.keepalive_count = keepalive_count
        self._connections = dict()
        self._connections_lock = ReadWriteLock()
        self._event_loop = wvmEventLoop()
        self._event_loop.start()

    def _search_connection(self, host, login, passwd, conn):
        self._connections_lock.acquireRead()
        try:
            if (host in self._connections):
                connections = self._connections[host]

                for connection in connections:
                    if (connection.login == login and connection.passwd == passwd and connection.type == conn):
                        return connection
        finally:
            self._connections_lock.release()

        return None

    def get_connection(self, host, login, passwd, conn):
        host = unicode(host)
        login = unicode(login)
        passwd = unicode(passwd) if passwd is not None else None
        connection = self._search_connection(host, login, passwd, conn)
        if (connection is None):
            self._connections_lock.acquireWrite()
            try:
                connection = self._search_connection(host, login, passwd, conn)
                if (connection is None):
                    connection = wvmConnection(host, login, passwd, conn)
                    if host in self._connections:
                        self._connections[host].append(connection)
                    else:
                        self._connections[host] = [connection]
            finally:
                self._connections_lock.release()

        elif not connection.connected:
            connection.connect()

        if connection.connected:
            return connection.connection
        else:
            raise libvirtError(connection.last_error)

    def host_is_up(self, conn_type, hostname):
        try:
            socket_host = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            socket_host.settimeout(1)
            if conn_type == CONN_SSH:
                if ':' in hostname:
                    LIBVIRT_HOST, PORT = (hostname).split(":")
                    PORT = int(PORT)
                else:
                    PORT = SSH_PORT
                    LIBVIRT_HOST = hostname
                socket_host.connect((LIBVIRT_HOST, PORT))
            if conn_type == CONN_TCP:
                socket_host.connect((hostname, TCP_PORT))
            if conn_type == CONN_TLS:
                socket_host.connect((hostname, TLS_PORT))
            socket_host.close()
            return True
        except Exception as err:
            return err

connection_manager = wvmConnectionManager(
    settings.LIBVIRT_KEEPALIVE_INTERVAL if hasattr(settings, 'LIBVIRT_KEEPALIVE_INTERVAL') else 5,
    settings.LIBVIRT_KEEPALIVE_COUNT if hasattr(settings, 'LIBVIRT_KEEPALIVE_COUNT') else 5
)


# class LibvirtErrorMsg():
#     CTX = '**[Error]** '
# 
# class LibvirtError():
#     """Subclass virError to get the last error information."""
#     def __init__(self, ctx,err):
#         msg = ctx + err[2]
#         BaseLogging.Logger(msg, level='error')
# 
# libvirt.registerErrorHandler(LibvirtError,LibvirtErrorMsg.CTX)

class VMBase(object):
         
    def getVolumeByPath(self,path):
        return self.conn.storageVolLookupByPath(path)
    
    def getIfaces(self):
        interface = []
        for inface in self.conn.listInterfaces():
            interface.append(inface)
        for inface in self.conn.listDefinedInterfaces():
            interface.append(inface)
        return interface
    
    def getStorages(self):
        storages = []
        for pool in self.conn.listStoragePools():
            storages.append(pool)
        for pool in self.conn.listDefinedStoragePools():
            storages.append(pool)
        return storages
    
    def getNetwork(self, net):
        try:
            return self.conn.networkLookupByName(net)
        except libvirt.libvirtError,e:
            return 'Reason:{result}'.format(result=e.get_error_message())          
    
    def close(self):
        try:
            return self.conn.close()
        except:
            return self.conn.close() 
            return False           

class VMServer(VMBase):
    def __init__(self,conn):
        self.conn = conn

    def defineXML(self, xml):
        '''Defining the incoming xml'''
        try:
            return self.conn.defineXML(xml)  
        except libvirt.libvirtError,e:
            return 'Reason:{result}'.format(result=e.get_error_message())  

    def getServerInfo(self):
        '''Get host basic information'''
        data = self.conn.getInfo()
        return {"cpu_arch":data[0],"mem":data[1],"cpu_total":data[2],"cpu_mhz":data[3]}


    def getVmServerisAlive(self):
        status = self.conn.isAlive()
        if status == 1:return 0
        else:return 1

    def getAliveInstance(self):
        '''Get all active instances'''
        domList = []
        for Id in self.conn.listDomainsID():
            dom = self.conn.lookupByID(Id)
            domList.append(dom.name())
        return domList
            
    
    def createInstance(self,dom_xml):
        '''Create a virtual machine'''
        try:
            dom = self.conn.defineXML(dom_xml)
            return dom.create()
        except libvirt.libvirtError,e:
            return 'Instance creation failed，Reason：{result}'.format(result=e.get_error_message())  
     
    def getVmStorageInfo(self):
        storage = []
        try:               
            vMdisk = self.conn.listStoragePools()
            for vM in vMdisk:
                data = {}
                pool = self.conn.storagePoolLookupByName(vM)
                pool_xml = pool.XMLDesc(0)
                pool_xml = minidom.parseString(pool_xml)
                try:
                    data['pool_type'] = pool_xml.getElementsByTagName('pool')[0].getAttribute('type')
                except:
                    data['pool_type'] = None
                try:
                    data['pool_path'] = pool_xml.getElementsByTagName('path')[0].childNodes[0].data
                except:
                    data['pool_path'] = None
                data['pool_name'] = pool.name()
                data['pool_size'] = pool.info()[1] / 1024/ 1024/ 1024
                data['pool_available'] = pool.info()[3] / 1024/ 1024/ 1024
                try:
                    data['pool_per'] = round((float(data['pool_size'] - data['pool_available']) / data['pool_size'])*100,2)
                except:
                    data['pool_per'] = 0
                data['pool_volumes'] = pool.numOfVolumes()
                data['pool_active'] = pool.isActive()
                storage.append(data)
            return storage
        except libvirt.libvirtError:                    
            return storage
        
    def getVmIsoList(self):
        isoList = []
        try:               
            vMdisk = self.conn.listStoragePools()
            for vM in vMdisk:
                pool = self.conn.storagePoolLookupByName(vM)
                stgvols = pool.listVolumes()
                for stgvolname in stgvols:
                    volData = dict()
                    stgvol = pool.storageVolLookupByName(stgvolname)
                    info = stgvol.info()
                    try:
                        volXml = stgvol.XMLDesc(0)
                        xml = minidom.parseString(volXml)
                        volData['vol_type'] = xml.getElementsByTagName('target')[0].getElementsByTagName('format')[0].getAttribute('type')
                    except:
                        volData['vol_type'] = 'unkonwn'
                    volData['vol_name'] = stgvol.name()
                    volData['vol_size'] = info[1] / 1024/ 1024/ 1024
                    volData['vol_available'] = info[2] / 1024/ 1024/ 1024
                    volData['vol_path'] = stgvol.path()
                    if volData['vol_type'].endswith('.iso') or volData['vol_path'].endswith('.iso'):isoList.append(volData)
            return isoList
        except libvirt.libvirtError:                    
            return isoList
        

    def getVmServerInfo(self):  
        '''Get host information'''
        try:
            data = self.conn.getInfo()
        except Exception:
            return False
        try:
            sysXml = minidom.parseString(self.conn.getSysinfo())
            cpu_model = sysXml.getElementsByTagName('processor')[0].getElementsByTagName('entry')[4].childNodes[0].data
        except: 
            cpu_model = None
        try:
            vm_type = self.conn.getType()
        except: 
            vm_type = None    
        try:    
            version = self.conn.getVersion()
        except:  
            version = None 
        try:    
            max_vcpu = self.conn.getMaxVcpus(None)
        except: 
            max_vcpu = None                           
        try:   
            active =  self.conn.numOfDomains()
            inactice = self.conn.numOfDefinedDomains()
            total = active + inactice                
        except:
            total = 0  
        if  self.conn.isAlive() == 1:status = 0
        else:status = 1
        try:
            # TEST BASLANGICI (Memory Kullanimi hatali geliyordu)

            #mem_per =  round((float(self.conn.getMemoryStats(0).get('total') - self.conn.getMemoryStats(0).get('free')) / self.conn.getMemoryStats(0).get('total'))*100,2)
            memUsageList = self.conn.getMemoryStats(libvirt.VIR_NODE_MEMORY_STATS_ALL_CELLS)
            mem_per =  round((float(memUsageList['total'] - (memUsageList['free'] + memUsageList['cached'])) / memUsageList['total'])*100,2)

            # TEST BITISI

        except:
            mem_per = 0
        vmStatus = self.getVmInstatus()
        return {"cpu_arch":data[0],"mem":data[1],"cpu_total":data[2],"mem_per":mem_per,
                'max_vcpu':max_vcpu,"status":status,"cpu_mhz":data[3],'ins':total,
                'type':vm_type,"version":version,'cpu_model':cpu_model,"vmStatus":vmStatus}                

    def getAllInstance(self):
        '''Get a list of all instances'''
        vList = []
        try:
            for dom in self.conn.listAllDomains():
                vList.append(dom.UUIDString())
            return vList
        except:
            return vList

    def getVmInstatus(self):
        '''Get instance status'''           
        rList = [] 
        pList = [] 
        sList = [] 
        data = dict()       
        for dom in self.conn.listAllDomains():
            domStatus = dom.state()[0]  
            if  domStatus ==  3:pList.append(dom.name())
            elif  domStatus ==  1:rList.append(dom.name())
            elif   domStatus ==  5:sList.append(dom.name())   
        data['stop'] = sList
        data['running'] = rList
        data['pause'] =  pList
        return data  


    def getVmInstanceBaseInfo(self,server_ip,server_id):
        '''Get basic information of all instances'''
        dataList = []
        for ins in self.conn.listAllDomains():
            raw_xml = ins.XMLDesc(0)
            xml = minidom.parseString(raw_xml)       
            try:
                cpu = xml.getElementsByTagName('vcpu')[0].getAttribute('current') 
                if len(cpu) == 0: cpu = xml.getElementsByTagName('vcpu')[0].childNodes[0].data   
            except:
                cpu = 0    
            try:
                mem = ins.info()[2] / 1024
            except:
                mem = 0   
            #Get vnc port information
            try:
                vnc_port = xml.getElementsByTagName('graphics')[0].getAttribute("port") 
            except:
                vnc_port = 0 
            #Get Title-Description information
            try:
                bdtitle = xml.getElementsByTagName('title')[0].firstChild.data
            except:
                bdtitle = " " 
            try:
                bddesc = xml.getElementsByTagName('description')[0].firstChild.data
            except:
                bddesc = " " 
            ntkList = []
            #Get host Mac address
            for nk in xml.getElementsByTagName('interface'):
                if nk.getElementsByTagName('mac') and nk.getElementsByTagName('target'):
                    ntkData = dict()
                    mac = nk.getElementsByTagName('mac')[0].getAttribute('address')
                    name = nk.getElementsByTagName('target')[0].getAttribute("dev")
                    ntkData['name'] = name
                    ntkData['mac'] = mac
                    ntkList.append(ntkData)
            #Get ip address
            ipaddress = []
            if ntkList:
                try:
                    data = ins.interfaceAddresses(1)
                except libvirt.libvirtError, ex:
                    print ex
                    data = None 
                if data:
                    for k,v in data.items():
                        ips = {}
                        if k != 'lo':
                            try:
                                ips[k] = v.get('addrs')[0] 
                                ipaddress.append(ips) 
                            except Exception ,ex:
                                pass                 
            data = dict()
            data["name"] = ins.name()
            data["status"] = ins.state()[0]
            data["cpu"] = cpu
            data["server_ip"] = server_ip
            data["server_id"] = server_id
            data["memo"] = mem
            data["bdtitle"] = bdtitle
            data["bddesc"] = bddesc
            data["vnc"] = vnc_port
            data['token'] = ins.UUIDString()
            data['netk'] = ntkList
            data['ip'] = ipaddress
            dataList.append(data)
        return dataList
    
    def getVmInstanceInfo(self,server_ip):  
        '''Query all instance information'''
        active =  self.conn.numOfDomains()
        inactice = self.conn.numOfDefinedDomains()
        total = active + inactice
        vms_active = []
        vms_inactive = []
        domain_list = self.conn.listDomainsID() + self.conn.listDefinedDomains() 
        vmPoolList = []
        pools = self.conn.listAllStoragePools()
        #Get the volume inside the storage pool
        for pls in pools:
            try:
                for vol in pls.listVolumes():
                    data = {}
                    data[pls.name()] = pls.storageVolLookupByName(vol).path()
                    vmPoolList.append(data)
            except libvirt.libvirtError:
                pass
        for dom in domain_list:
            domData = {}
            if isinstance(dom,int): insName = self.conn.lookupByID(dom).name()
            else:insName = dom
            instance = self.conn.lookupByName(insName)
            status = instance.state()
            domData['status'] = status[0]   
            raw_xml = instance.XMLDesc(0)
            xml = minidom.parseString(raw_xml)
            diskList = []
            #Get instance disk information
            for disk in xml.getElementsByTagName('disk'):
                #Determine the device type is not a disk
                if disk.getAttribute("device") == 'disk':
                    if disk.getElementsByTagName('source'):
                        data = {}
                        try:
                            disk_name = disk.getElementsByTagName('source')[0].getAttribute("file") 
                        except:
                            disk_name = disk.getElementsByTagName('source')[0].getAttribute("dev")
                        #Determine the volume exists in that storage pool
                        for vol in vmPoolList:
                            for p,v in vol.iteritems():
                                if disk_name == v:data['disk_pool'] = p
                        data['disk_path'] = disk_name
                        data['disk_sn'] = disk.getElementsByTagName('target')[0].getAttribute("dev")
                        try:
                            data['disk_size'] = instance.blockInfo(disk_name)[0]  / 1024 /1024/1024
                            data['disk_capacity'] = instance.blockInfo(disk_name)[1]   / 1024 /1024/1024
                            data['disk_per'] = round(float(data['disk_capacity'])/data['disk_size']*100,2)
                        except:
                            data['disk_size'] = 0
                            data['disk_capacity'] = 0  
                            data['disk_per'] = 0                   
                        diskList.append(data)
          
            #Get the NIC name of the VM instance
            nkList = []
            for nk in xml.getElementsByTagName('interface'):
                if nk.getElementsByTagName('target'):
                    nk_name = nk.getElementsByTagName('target')[0].getAttribute("dev")                           
                    nkList.append(nk_name)                     
            
            #Get network card ip address
            ipaddress = []
            if nkList:
                try:
                    data = instance.interfaceAddresses(1)
                except libvirt.libvirtError, ex:
                    print ex 
                if data:
                    for k,v in data.items():
                        ips = {}
                        if k != 'lo':
                            try:
                                ips[k] = v.get('addrs')[0] 
                                ipaddress.append(ips) 
                            except Exception ,ex:
                                pass 
            #Get the VM instance memory capacity information
            try:
                mem = instance.info()[2] / 1024
            except:
                mem = 0   
                
            #Mem utilization and ip address
            try:
                if status[0] == 5:domData['mem_per'] = 0
                else:
                    #mem_per =  round(float(instance.memoryStats().get('rss')) / instance.memoryStats().get('actual')*100,2)
                    #emre test
                    used_ram = float(instance.memoryStats().get('available') - instance.memoryStats().get('unused'))/1024
                    total_ram = instance.memoryStats().get('available') / 1024
                    mem_per =  round((used_ram / total_ram) * 100,2)
                    print insName, "used_ram : ", used_ram
                    #emre test son
                    if mem_per > 100:domData['mem_per'] = 100
                    else:domData['mem_per'] = mem_per
                    
            except Exception,e:     
                domData['mem_per'] = 0


            #Get virtual machine instance CPU information
            try:
                cpu = xml.getElementsByTagName('vcpu')[0].getAttribute('current') 
                if len(cpu) == 0: cpu = xml.getElementsByTagName('vcpu')[0].childNodes[0].data   
            except:
                cpu = 0    
            
            #Get vnc port information
            try:
                vnc_port = xml.getElementsByTagName('graphics')[0].getAttribute("port") 
            except:
                vnc_port = 0                                       
            domData['name'] = insName
            domData['disks'] = diskList
            domData['desc'] = "BBBB"
            domData['netk'] = nkList
            domData['mem'] = mem 
            domData['cpu'] = cpu
            domData['vnc'] = vnc_port
            #Generate tokens for noVNC
            domData['token'] = TokenUntils.makeToken(str=server_ip+domData['name'])             
            domData['ip'] = ipaddress
            if isinstance(dom,int):vms_active.append(domData)
            else:vms_inactive.append(domData)   
        return {"total":total,
                "active":{"total":active,"number":vms_active},
                "inactice":{"total":inactice,"number":vms_inactive}}                 
 

   
                 
class VMStorage(VMBase):
    def __init__(self,conn):
        self.conn =  conn
  
    def defineXML(self, xml):
        '''Defining the incoming xml'''
        try:
            return self.conn.defineXML(xml)  
        except libvirt.libvirtError,e:
            return 'Failed to create storage pool，Reason：{result}'.format(result=e.get_error_message())          
     
    def getStoragePool(self,pool_name):
        '''Query storage pool'''
        try:
            pool = self.conn.storagePoolLookupByName(pool_name) 
            return pool
        except libvirt.libvirtError:
            return False 
    
    def getPoolXMLDesc(self,pool_name):
        try:
            pool = self.conn.storagePoolLookupByName(pool_name) 
            return pool.XMLDesc(0)
        except libvirt.libvirtError,e: 
            return 'Failed to get storage pool information, Reason：{result}'.format(result=e.get_error_message())    
    
    def getVolumeXMLDesc(self,pool,volume_name):
        try: 
            volume = pool.storageVolLookupByName(volume_name)
            return volume.XMLDesc(0)
        except libvirt.libvirtError,e: 
            return 'Failed to get volume information, Reason：{result}'.format(result=e.get_error_message())  

    
    def getStorageInfo(self,pool_name):
        '''Get information for a single storage pool'''
        data = {}
        try:           
            pool = self.conn.storagePoolLookupByName(pool_name)
            pool_xml = pool.XMLDesc(0)
            pool_xml = minidom.parseString(pool_xml)
            try:
                data['pool_type'] = pool_xml.getElementsByTagName('pool')[0].getAttribute('type')
            except:
                data['pool_type'] = None
            try:
                data['pool_path'] = pool_xml.getElementsByTagName('path')[0].childNodes[0].data
            except:
                data['pool_path'] = None
            data['pool_name'] = pool.name()
            data['pool_size'] = pool.info()[1] / 1024/ 1024/ 1024
            data['pool_available'] = pool.info()[3] / 1024/ 1024/ 1024
            data['pool_per'] = round((float(data['pool_size'] - data['pool_available']) / data['pool_size'])*100,2)
            data['pool_volumes'] = pool.numOfVolumes()
            data['pool_active'] = pool.isActive()
            volList = []
            stgvols = pool.listVolumes()
            for stgvolname in stgvols:
                volData = dict()
                stgvol = pool.storageVolLookupByName(stgvolname)
                info = stgvol.info()
                try:
                    volXml = stgvol.XMLDesc(0)
                    xml = minidom.parseString(volXml)
                    volData['vol_type'] = xml.getElementsByTagName('target')[0].getElementsByTagName('format')[0].getAttribute('type')
                except:
                    volData['vol_type'] = 'unkonwn'
                volData['vol_name'] = stgvol.name()
                volData['vol_size'] = info[1] / 1024/ 1024/ 1024
                volData['vol_available'] = info[2] / 1024/ 1024/ 1024
                volData['vol_path'] = stgvol.path()
                try:
                    volData['vol_per'] = round((float(volData['vol_available']) / volData['vol_size'])*100,2)
                except:
                    volData['vol_per'] = 100
                volList.append(volData)
            data['pool_vols'] = volList
            return data
        except libvirt.libvirtError:                   
            return data 
 
    def getStorageVolume(self,pool,volume_name):
        '''Query whether the volume exists'''
        try:
            return pool.storageVolLookupByName(volume_name)
        except libvirt.libvirtError:  
            return False        
        
    def createStoragePool(self,pool_xml):
        '''Create a storage pool'''
        try:
            pool = self.conn.storagePoolDefineXML(pool_xml)
            if pool:
                pool.build(0)
                pool.create(0)    
                pool.setAutostart(1)
                return pool.refresh()#Refresh the newly added storage pool and load the existing files in the storage pool
        except libvirt.libvirtError,e: 
            return 'Failed to create the storage pool, Reason:{result}'.format(result=e.get_error_message()) 
    
    def refreshStoragePool(self,pool):
        '''Refresh the storage pool'''
        try:
            return pool.refresh()
        except libvirt.libvirtError,e:
            return 'Failed to create the storage pool, Reason:{result}'.format(result=e.get_error_message()) 
    
    def createVolumes(self,pool,volume_name,volume_capacity,drive=None):
        if drive is None:drive = 'qcow2'
        volume_xml = """<volume>
                            <name>{volume_name}</name>
                            <allocation>0</allocation>
                            <capacity unit="G">{volume_capacity}</capacity>
                            <target> 
                                <format type="{drive}"/> 
                            </target>                             
                        </volume>
        """        
        volume_xml = volume_xml.format(volume_name=volume_name,volume_capacity=volume_capacity,drive=drive)
        try:
            return pool.createXML(volume_xml, 0)
        except libvirt.libvirtError,e:
            return 'Failed to create the storage pool, Reason:{result}'.format(result=e.get_error_message()) 

        
    def deleteVolume(self,pool,volume_name):
        volume = pool.storageVolLookupByName(volume_name)
#             volume.wipe(0)
        try:
            return volume.delete(0)#Volume.delete(0) is deleted from the storage pool, volume.wipe(0), is deleted from the disk
        except libvirt.libvirtError:
            return False

        
    def autoStart(self,pool):
        '''Set storage pool self-start'''
        if pool.autostart() == True:
            return pool.setAutostart(0)
        else:
            return pool.setAutostart(1)
        
    
    def deleteStoragePool(self,pool):
        '''Delete storage pool'''
        try:
            pool.destroy()
            return pool.undefine()
        except libvirt.libvirtError,e:
            return 'Delete failed, Reason:{result}'.format(result=e.get_error_message())
    

    
    def getStorageMode(self,pool_name):
        '''Get the type of storage pool'''
        return  vMUtil.get_xml_path(self.getPoolXMLDesc(pool_name), "/pool/@type")
    
    def getStorageVolumeXMLDesc(self,pool,name):
        vol = self.getStorageVolume(pool,name)
        return vol.XMLDesc(0)
    
    
    def getStorageVolumeType(self, pool,name):
        '''Get the type of volume'''
        vol_xml = self.getStorageVolumeXMLDesc(name)
        return vMUtil.get_xml_path(vol_xml, "/volume/target/format/@type")
    
    def clone(self, pool,pool_name,name, clone, format=None):
        '''Clone volume'''
        storage_type = self.getStorageMode(pool_name)
        if storage_type == 'dir':
            clone += '.img'
        vol = self.getStorageVolume(pool,name)
        if vol:
            if not format:
                format = self.getStorageVolumeType(name)
            xml = """
                <volume>
                    <name>%s</name>
                    <capacity>0</capacity>
                    <allocation>0</allocation>
                    <target>
                        <format type='%s'/>
                    </target>
                </volume>""" % (clone, format)
            try:
                return self.createXMLFrom(xml, vol, 0)
            except libvirt.libvirtError,e:
                return 'Failed to clone the virtual machine, Reason:{result}'.format(result=e.get_error_message())   
                     
    def createXMLFrom(self,pool,xml, vol, flags):
        try:
            return pool.createXMLFrom(xml, vol, flags)        
        except libvirt.libvirtError,e:
            return 'Create failed, Reason:{result}'.format(result=e.get_error_message())      
           
class VMInstance(VMBase):
    def __init__(self,conn):
        self.conn = conn         

    def queryInstance(self,id=None,name=None):
        '''Query whether the virtual machine instance exists'''
        instance = None
        if isinstance(id, int):
            try:
                instance = self.conn.lookupByID(id)
                return instance
            except libvirt.libvirtError:
                return False
        elif isinstance(name, str):
            try:
                instance = self.conn.lookupByName(name)
                return instance
            except libvirt.libvirtError:
                return False
            
    def getInsUUID(self,instance):
        return instance.UUIDString()            
            
    def defineXML(self, xml):
        '''Defining the incoming xml'''
        try:
            return self.conn.defineXML(xml) 
        except libvirt.libvirtError,e:
            return 'Reason:{result}'.format(result=e.get_error_message())             
            
    def getInsXMLDesc(self,instance,flag):
        try:
            return instance.XMLDesc(flag)
        except libvirt.libvirtError,e:
            return 'Reason:{result}'.format(result=e.get_error_message())          
    
    def managedSave(self, instance):
        try:
            return instance.managedSave(0)
        except libvirt.libvirtError,e:
            return 'Reason:{result}'.format(result=e.get_error_message())          

    def managedSaveRemove(self, instance):
        try:
            return instance.managedSaveRemove(0)
        except libvirt.libvirtError,e:
            return 'Reason:{result}'.format(result=e.get_error_message())  
    
    
    def umountIso(self,instance, dev, image):
        '''Uninstall Cdrom'''
        '''
        @param dev: Device serial number, such as hda
        @param images: /opt/iso/CentOS-6.3-x86_64-bin-DVD1.iso  
        '''
        tree = ElementTree.fromstring(self.getInsXMLDesc(instance,0))        
        for disk in tree.findall('devices/disk'):
            if disk.get('device') == 'cdrom':
                for elm in disk:
                    if elm.tag == 'source':
                        if elm.get('file') == image:
                            src_media = elm
                    if elm.tag == 'target':
                        if elm.get('dev') == dev:
                            try:
                                disk.remove(src_media)
                                if instance.state()[0] == 1:
                                    xml_disk = ElementTree.tostring(disk)
                                    try:
                                        instance.attachDevice(xml_disk)
                                    except libvirt.libvirtError,e:
                                        return 'Uninstall failed, Reason:{result}'.format(result=e.get_error_message())                                
                                    xmldom = self.getInsXMLDesc(instance,1)
                                if instance.state()[0] == 5:
                                    xmldom = ElementTree.tostring(tree)
                                try:
                                    return self.defineXML(xmldom)
                                except libvirt.libvirtError,e:
                                    return 'Uninstall failed, Reason:{result}'.format(result=e.get_error_message())                                
                            except:
                                return False
                                

        
        
    
    def mountIso(self,instance,dev, image):
        tree = ElementTree.fromstring(self.getInsXMLDesc(instance,0))
        for disk in tree.findall('devices/disk'):
            if disk.get('device') == 'cdrom':
                for elm in disk:
                    if elm.tag == 'target':
                        if elm.get('dev') == dev:
                            src_media = ElementTree.Element('source')
                            src_media.set('file', image)
                            disk.append(src_media)
                            if instance.state()[0] == 1:
                                xml_disk = ElementTree.tostring(disk)
                                try:
                                    instance.attachDevice(xml_disk)
                                except libvirt.libvirtError,e:
                                    return 'Mount failed, Reason:{result}'.format(result=e.get_error_message()) 
                                xmldom = self.getInsXMLDesc(instance,1)
                            if instance.state()[0] == 5:
                                xmldom = ElementTree.tostring(tree)
                            try:
                                return self.defineXML(xmldom)
                            except libvirt.libvirtError,e:
                                return 'Uninstall failed, Reason:{result}'.format(result=e.get_error_message()) 
        
  
    
     
    def changeSettings(self,instance,description, cur_memory, memory, cur_vcpu, vcpu):
        """
        Function change ram and cpu on vds.
        """
        memory = int(memory) * 1024
        cur_memory = int(cur_memory) * 1024

        xml = instance.XMLDesc(1)
        tree = ElementTree.fromstring(xml)

        set_mem = tree.find('memory')
        set_mem.text = str(memory)
        set_cur_mem = tree.find('currentMemory')
        set_cur_mem.text = str(cur_memory)
        set_desc = tree.find('description')
        set_vcpu = tree.find('vcpu')
        set_vcpu.text = vcpu
        set_vcpu.set('current', cur_vcpu)

        if not set_desc:
            tree_desc = ElementTree.Element('description')
            tree_desc.text = description
            tree.insert(2, tree_desc)
        else:
            set_desc.text = description

        new_xml = ElementTree.tostring(tree)
        return self.defineXML(new_xml)     
       
    
    def getVmInstanceInfo(self,instance,server_ip,vMname):
        '''Query single instance information'''
        vmPoolList = []
        pools = self.conn.listAllStoragePools()
        #Get the volume inside the storage pool
        for pls in pools:
            try:
                for vol in pls.listVolumes():
                    data = {}
                    data[pls.name()] = pls.storageVolLookupByName(vol).path()
                    vmPoolList.append(data)                 
            except libvirt.libvirtError:
                pass
        if instance:
            domData = {}
            status = instance.state()
            domData['status'] = status[0]   
            raw_xml = instance.XMLDesc(0)
            xml = minidom.parseString(raw_xml)
            diskList = []
            # Get the disk information of the instance
            for disk in xml.getElementsByTagName('disk'):
                # determine the device type is not a disk
                if disk.getAttribute("device") == 'disk':
                    if disk.getElementsByTagName('source'):
                        data = {}
                        try:
                            disk_name = disk.getElementsByTagName('source')[0].getAttribute("file") 
                        except:
                            disk_name = disk.getElementsByTagName('source')[0].getAttribute("dev")
                        #Judge the volume exists in that storage pool
                        for vol in vmPoolList:
                            for p,v in vol.iteritems():
                                if disk_name == v:data['disk_pool'] = p
                        data['disk_path'] = disk_name
                        data['disk_sn'] = disk.getElementsByTagName('target')[0].getAttribute("dev")
                        try:
                            data['disk_size'] = instance.blockInfo(disk_name)[0]  / 1024 /1024/1024
                            data['disk_capacity'] = instance.blockInfo(disk_name)[1]   / 1024 /1024/1024
                            data['disk_per'] = round(float(data['disk_capacity'])/data['disk_size']*100,2)
                        except:
                            data['disk_size'] = 0
                            data['disk_capacity'] = 0  
                            data['disk_per'] = 0                   
                        diskList.append(data)
           
            ''' TEST BASLANGICI '''

            #Get Title-Description information
            try:
                bdtitle = xml.getElementsByTagName('title')[0].firstChild.data
            except:
                bdtitle = " " 
            try:
                bddesc = xml.getElementsByTagName('description')[0].firstChild.data
            except:
                bddesc = " "
            try:
                max_memory = int(xml.getElementsByTagName('memory')[0].firstChild.data) / 1024
            except:
                max_memory = 0
            try:    
                max_vcpu = xml.getElementsByTagName('vcpu')[0].firstChild.data
            except: 
                max_vcpu = None  

            ''' TEST BITISI '''


            # Obtain the NIC name of the VM instance
            nkList = []
            for nk in xml.getElementsByTagName('interface'):
                if nk.getElementsByTagName('target'):
                    nk_name = nk.getElementsByTagName('target')[0].getAttribute("dev")                           
                    nkList.append(nk_name)      
            # Get network card ip address
            ipaddress = []
            if nkList:
                data = self.getInterFaceIpAddress(instance, 1) 
                if data:
                    for k,v in data.items():
                        ips = {}
                        if k != 'lo':
                            try:
                                ips[k] = v.get('addrs')[0] 
                                ipaddress.append(ips) 
                            except Exception ,ex:
                                pass 
            #Get the VM instance memory capacity information
            try:
                mem = instance.info()[2] / 1024
            except:
                mem = 0   

            #Mem utilization and ip address
            try:
                if status[0] == 5:domData['mem_per'] = 0
                else:
                    mem_per =  round(float(instance.memoryStats().get('rss')) / instance.memoryStats().get('actual')*100,2)
                    if mem_per > 100:domData['mem_per'] = 100
                    else:domData['mem_per'] = mem_per
                    
            except Exception,e:     
                domData['mem_per'] = 0


            #Get virtual machine instance CPU information
            try:
                cpu = xml.getElementsByTagName('vcpu')[0].getAttribute('current') 
                if len(cpu) == 0: cpu = xml.getElementsByTagName('vcpu')[0].childNodes[0].data   
            except:
                cpu = 0    
            #Get vnc port information
            try:
                vnc_port = xml.getElementsByTagName('graphics')[0].getAttribute("port") 
            except:
                vnc_port = 0                                                   
            domData['disks'] = diskList
            domData['netk'] = nkList
            domData['mem'] = mem 
            domData['max_mem'] = max_memory
            domData['max_vcpu'] = max_vcpu
            domData['cpu'] = cpu
            domData['vnc'] = vnc_port
            domData['name'] = vMname
            domData['bddesc'] = bddesc
            domData['bdtitle'] = bdtitle
            #Generate tokens for noVNC
            domData['token'] = TokenUntils.makeToken(str=server_ip+vMname)
            domData['ip'] = ipaddress
            return domData

    def getMediaDevice(self,instance):
        '''Get cdrom'''
        def disks(ctx):
            result = []
            dev = None
            volume = None
            storage = None
            src_path = None
            for media in ctx.xpathEval('/domain/devices/disk'):
                device = media.xpathEval('@device')[0].content
                if device == 'cdrom':
                    try:
                        dev = media.xpathEval('target/@dev')[0].content
                        try:
                            src_path = media.xpathEval('source/@file')[0].content
                            vol = self.getVolumeByPath(src_path)
                            volume = vol.name()
                            stg = vol.storagePoolLookupByVolume()
                            storage = stg.name()
                        except:
                            src_path = media.xpathEval('source/@file')[0].content
                            volume = media.xpathEval('source/@file')[0].content.split('/')[-1]
                    except:
                        src_path = None
                        volume = None
                    finally:
                        result.append({'dev': dev, 'image': volume, 'storage': storage, 'path': src_path})
            return result
        return vMUtil.get_xml_path(self.getInsXMLDesc(instance,0), func=disks)
    
    
    def delDisk(self,instance):
        '''Delete Disk When Deleting a Virtual Machine'''
        disks = self.getDiskDevice(instance)
        for disk in disks:
            try:
                vol = self.getVolumeByPath(disk.get('path'))
                vol.delete(0)
            except:
                pass
    
    def getDiskDevice(self,instance):
        '''Get the instance of the disk device'''
        def disks(ctx):
            result = []
            dev = None
            volume = None
            storage = None
            src_path = None
            for disk in ctx.xpathEval('/domain/devices/disk'):
                device = disk.xpathEval('@device')[0].content
                if device == 'disk':
                    try:
                        dev = disk.xpathEval('target/@dev')[0].content
                        src_path = disk.xpathEval('source/@file|source/@dev|source/@name')[0].content
                        try:
                            vol = self.getVolumeByPath(src_path)
                            volume = vol.name()
                            stg = vol.storagePoolLookupByVolume()
                            storage = stg.name()
                        except:
                            volume = src_path
                    except:
                        pass
                    finally:
                        result.append({'dev': dev, 'image': volume, 'storage': storage, 'path': src_path})
            return result
        return vMUtil.get_xml_path(self.getInsXMLDesc(instance,0), func=disks)
    
    
    def clone(self, instance,clone_data):
        '''Clone an instance'''
        clone_dev_path = []
        xml = self.getInsXMLDesc(instance, flag=1)
        tree = ElementTree.fromstring(xml)
        name = tree.find('name')
        name.text = clone_data['name']
        uuid = tree.find('uuid')
        tree.remove(uuid)
        for num, net in enumerate(tree.findall('devices/interface')):
            elm = net.find('mac')
            inter = net.find('target')
            brName = net.find('source').get('bridge')
            inter.set('dev',brName + '-' + CommTools.radString(4))
            elm.set('address', vMUtil.randomMAC())
        
        for disk in tree.findall('devices/disk'):
            if disk.get('device') == 'disk':
                elm = disk.find('target')
                device_name = elm.get('dev')
                if device_name:
                    target_file = clone_data['disk']
                    try:
                        meta_prealloc = clone_data['meta']
                    except:
                        meta_prealloc = False
                    elm.set('dev', device_name)
                elm = disk.find('source')
                source_file = elm.get('file')
                if source_file:
                    clone_dev_path.append(source_file)
                    clone_path = os.path.join(os.path.dirname(source_file),
                                              target_file)
                    elm.set('file', clone_path)
                    vol = self.getVolumeByPath(source_file)
                    vol_format = vMUtil.get_xml_path(vol.XMLDesc(0),"/volume/target/format/@type")
                    if vol_format == 'qcow2' and meta_prealloc:
                        meta_prealloc = True
                    vol_clone_xml = """
                                    <volume>
                                        <name>%s</name>
                                        <capacity>0</capacity>
                                        <allocation>0</allocation>
                                        <target>
                                            <format type='%s'/>
                                        </target>
                                    </volume>""" % (target_file, vol_format)
                    stg = vol.storagePoolLookupByVolume()
                    stg.createXMLFrom(vol_clone_xml, vol, meta_prealloc)
        if self.defineXML(ElementTree.tostring(tree)):return 0
    
    def getCpuUsage(self,instance):       
        if instance.state()[0] == 1:
#             nbcore = self.conn.getInfo()[2] #The number of cpu nodes
            nbcore = instance.info()[3] #Number of virtual CPUs, doubts
            cpu_use_ago = instance.info()[4]
            time.sleep(1)
            cpu_use_now = instance.info()[4]
            diff_usage = cpu_use_now - cpu_use_ago
            cpu_per = 100 * diff_usage / (1 * nbcore * 10 ** 9L)
        else:
            cpu_per = 0
        return cpu_per

    def getNetUsage(self,instance):
        devices = []
        dev_usage = []
        tree = ElementTree.fromstring(self.getInsXMLDesc(instance, flag=1))
        if instance.state()[0] == 1:
            tree = ElementTree.fromstring(self.getInsXMLDesc(instance, flag=1))
            for target in tree.findall("devices/interface/target"):
                devices.append(target.get("dev"))
            for i, dev in enumerate(devices):
                rx_use_ago = instance.interfaceStats(dev)[0]
                tx_use_ago = instance.interfaceStats(dev)[4]
                time.sleep(1)
                rx_use_now = instance.interfaceStats(dev)[0]
                tx_use_now = instance.interfaceStats(dev)[4]
                rx_diff_usage = (rx_use_now - rx_use_ago) * 8
                tx_diff_usage = (tx_use_now - tx_use_ago) * 8
                dev_usage.append({'dev': i, 'rx': rx_diff_usage, 'tx': tx_diff_usage})
        else:
            for i, dev in enumerate(self.get_net_device(instance)):
                dev_usage.append({'dev': i, 'rx': 0, 'tx': 0})
        return dev_usage

    def getDiskUsage(self,instance):
        devices = []
        dev_usage = []
        tree = ElementTree.fromstring(self.getInsXMLDesc(instance, flag=1))
        for disk in tree.findall('devices/disk'):
            if disk.get('device') == 'disk':
                dev_file = None
                dev_bus = None
                network_disk = True
                for elm in disk:
                    if elm.tag == 'source':
                        if elm.get('protocol'):
                            dev_file = elm.get('protocol')
                            network_disk = True
                        if elm.get('file'):
                            dev_file = elm.get('file')
                        if elm.get('dev'):
                            dev_file = elm.get('dev')
                    if elm.tag == 'target':
                        dev_bus = elm.get('dev')
                if (dev_file and dev_bus) is not None:
                    if network_disk:
                        dev_file = dev_bus
                    devices.append([dev_file, dev_bus])
        for dev in devices:
            if instance.state()[0] == 1:
                rd_use_ago = instance.blockStats(dev[0])[1]
                wr_use_ago = instance.blockStats(dev[0])[3]
                time.sleep(2)
                rd_use_now = instance.blockStats(dev[0])[1]
                wr_use_now = instance.blockStats(dev[0])[3]
                rd_diff_usage = rd_use_now - rd_use_ago
                wr_diff_usage = wr_use_now - wr_use_ago
            else:
                rd_diff_usage = 0
                wr_diff_usage = 0
            dev_usage.append({'dev': dev[1], 'rd': rd_diff_usage, 'wr': wr_diff_usage})
        return dev_usage
    
    def addInstanceDisk(self,instance,volPath):
        diskSn = 'vda'
        diskList = ['vd'+chr(i) for i in range(97,123)]
        domXml = instance.XMLDesc(0)
        tree = ElementTree.fromstring(domXml)
        for ds in tree.findall('devices/disk'):
            device = ds.get('device')
            vdisk = ds.find('target').get('dev')
            if device == 'disk' and vdisk in diskList:diskSn = diskList[diskList.index(vdisk) + 1]
        diskXml = Const.CreateDisk(volume_path=volPath, diskSn=diskSn)
        try:
            return instance.attachDeviceFlags(diskXml,3)#Flags is 3 if it is off. Ensure that the added hard disk will not be lost if restarted. 
        except libvirt.libvirtError,e:
            return 'Instance failed to add hard disk, Reason:{result}'.format(result=e.get_error_message()) 

    def addInstanceCdrom(self,instance,isoPath):
        diskSn = 'hdb'
        diskList = ['hd'+chr(i) for i in range(97,123)]
        domXml = instance.XMLDesc(0)
        tree = ElementTree.fromstring(domXml)
        for ds in tree.findall('devices/disk'):
            device = ds.get('device')
            vdisk = ds.find('target').get('dev')
            if device == 'cdrom' and vdisk in diskList:diskSn = diskList[diskList.index(vdisk) + 1]
        domXml = instance.XMLDesc(0)
        root = ElementTree.fromstring(domXml)
        dev = root.find('./devices')
        cmXml = ElementTree.SubElement(dev,'disk')
        cmXml.set('type','file')
        cmXml.set('device','cdrom')
        drXml = ElementTree.SubElement(cmXml,'driver')
        drXml.set('name','qemu')
        srxml = ElementTree.SubElement(cmXml,'source')
        srxml = srxml.set('file',isoPath)
        tgxml = ElementTree.SubElement(cmXml,'target')
        tgxml = tgxml.set('dev',diskSn)
        ElementTree.SubElement(cmXml,'readonly')
        domXml = ElementTree.tostring(root)
        try:
            return self.defineXML(domXml)#Flags is 3 if it is off. Ensure that the added hard disk will not be lost if restarted. 
        except libvirt.libvirtError,e:
            return 'Instance failed to add optical drive, Reason:{result}'.format(result=e.get_error_message())       
    
    def delInstanceCdrom(self,instance,cdrom):
        '''Remove the optical drive'''
        raw_xml = instance.XMLDesc(0) 
        root = ElementTree.fromstring(raw_xml) 
        for dk in root.findall('./devices'):
            devs = dk.getchildren()
            for dev in devs:
                if dev.tag == 'disk'and dev.get('device')=='cdrom':
                    for iter in dev:
                        if iter.tag == 'target' and iter.get('dev') == cdrom:
                            devs.remove(dev)
        diskXml = ElementTree.tostring(root)      
        try:
            return self.defineXML(diskXml)
        except libvirt.libvirtError,e:
            return 'Instance failed to remove the optical drive, Reason:{result}'.format(result=e.get_error_message()) 

    
    
    def addInstanceInterface(self,instance,brName):
        netk = self.getNetwork(brName)
        if netk:     
            xml = netk.XMLDesc(0)
            tree = ElementTree.fromstring(xml)
            try:
                mode = tree.find('virtualport').get('type') 
            except:
                mode = 'brctl'
            model = tree.find('forward').get('mode')               
            interXml = Const.CreateNetcard(nkt_br=brName, ntk_name=brName +'-'+CommTools.radString(length=4), data={'type':model,'mode':mode})
            try:
                return instance.attachDeviceFlags(interXml,3)#Flags is 3 if it is off. Ensure that the added hard disk will not be lost if restarted. 
            except libvirt.libvirtError,e:
                return 'Failed to add the network adapter to the instance, Reason:{result}'.format(result=e.get_error_message()) 
        else:return False 

        
    def delInstanceInterface(self,instance,interName): 
        '''Delete network device''' 
        interXml = None
        raw_xml = instance.XMLDesc(0)
        domXml = minidom.parseString(raw_xml)
        for ds in domXml.getElementsByTagName('interface'):
            try:
                dev = ds.getElementsByTagName('target')[0].getAttribute('dev')
            except:
                continue
            if dev == interName:interXml = ds.toxml()  
        if  interXml:
            try:
                return instance.detachDeviceFlags(interXml,3)
            except libvirt.libvirtError,e:
                return 'Instance network card deletion failed, Reason:{result}'.format(result=e.get_error_message()) 
        else:return False  
        
    def delInstanceDisk(self,instance,volPath):
        '''Delete the hard disk'''
        diskXml = None
        raw_xml = instance.XMLDesc(0)
        domXml = minidom.parseString(raw_xml)
        for ds in domXml.getElementsByTagName('disk'):
            try:
                path = ds.getElementsByTagName('source')[0].getAttribute('file')
            except:
                continue
            if path == volPath:diskXml = ds.toxml()  
        if diskXml:
            try:
                return instance.detachDeviceFlags(diskXml,3)
            except libvirt.libvirtError,e:
                return 'Instance failed to delete the hard disk, Reason:{result}'.format(result=e.get_error_message()) 
        else:return False
    
    def getInterFace(self,instance,inter_name):
        '''Get network card type'''
        def interface(ctx):
            result = dict()
            for media in ctx.xpathEval('/domain/devices/interface'):
                interface = media.xpathEval('target/@dev')[0].content
                if interface == inter_name:
                    try:
                        mode = media.xpathEval('virtualport/@type')[0].content
                    except:
                        mode = 'brct'
                    result['name'] =  interface
                    result['type'] = mode  
            return result
        return vMUtil.get_xml_path(instance.XMLDesc(0) , func=interface)        

    def get_net_device(self,instance):
        def get_mac_ipaddr(net, mac_host):
            def fixed(ctx):
                for net in ctx.xpathEval('/network/ip/dhcp/host'):
                    mac = net.xpathEval('@mac')[0].content
                    host = net.xpathEval('@ip')[0].content
                    if mac == mac_host:
                        return host
                return None
            print vMUtil.get_xml_path(net.XMLDesc(0), func=fixed)
            return vMUtil.get_xml_path(net.XMLDesc(0), func=fixed)

        def networks(ctx):
            result = []
            for net in ctx.xpathEval('/domain/devices/interface'):
                mac_host = net.xpathEval('mac/@address')[0].content
                nic_host = net.xpathEval('source/@network|source/@bridge|source/@dev')[0].content
                try:
                    net = self.getNetwork(nic_host)
                    ip = get_mac_ipaddr(net, mac_host)
                except:
                    ip = None
                result.append({'mac': mac_host, 'nic': nic_host, 'ip': ip})
            return result

        return vMUtil.get_xml_path(instance.XMLDesc(0), func=networks)

    def getInterFaceIpAddress(self,instance,source):
        '''Get virtual machine IP address'''
        try:
            return instance.interfaceAddresses(source)
        except libvirt.libvirtError, ex:
            print ex
            return {}
            
    def setInterfaceBandwidth(self,instance,port,bandwidth):
        '''Limit traffic'''
        domXml = instance.XMLDesc(0)
        root = ElementTree.fromstring(domXml)
        try:
            for dev in root.findall('.//devices/'):
                if dev.tag == 'interface':
                    for iter in dev:
                        if iter.tag == 'target' and iter.get('dev') == port:
                            bwXml = ElementTree.SubElement(dev,'bandwidth')   
                            inbdXml = ElementTree.Element('inbound')
                            inbdXml.set('average',str(int(bandwidth)*1024))
                            inbdXml.set('peak',str(int(bandwidth)*1024))
                            inbdXml.set('burst','1024')
                            outbdXml = ElementTree.Element('outbound')
                            outbdXml.set('average',str(int(bandwidth)*1024))
                            outbdXml.set('peak',str(int(bandwidth)*1024))
                            outbdXml.set('burst','1024')
                            bwXml.append(inbdXml)
                            bwXml.append(outbdXml)
            domXml = ElementTree.tostring(root)
        except Exception,e:
            return {"status":"faild",'data':e}
        if self.defineXML(domXml):return {"status":"success",'data':None} 
    
    def cleanInterfaceBandwidth(self,instance,port):
        '''Clear traffic limit'''
        domXml = instance.XMLDesc(0)
        root = ElementTree.fromstring(domXml)
        try:
            for dev in root.findall('.//devices/'):
                if dev.tag == 'interface':
                    for iter in dev:
                        if iter.get('dev') == port:
                            for iter in dev:
                                if iter.tag == 'bandwidth':dev.remove(iter) 
            domXml = ElementTree.tostring(root)
        except Exception,e:
            return {"status":"faild",'data':e}
        if self.defineXML(domXml):return {"status":"success",'data':None}     
        
    def getInstanceIsActive(self,instance):
        if instance.isActive():status = 0  
        else:status = 1      
        return status     
    
    # TEST BASLANGICI  
    def setVcpu(self,instance,cpu):
        # Adjust the number of CPUs
        if isinstance(cpu, int):
            try:
                return instance.setVcpusFlags(cpu,0)
            except libvirt.libvirtError,e:
                return 'Instance CPU adjustment failed. Reasons for the failure:{result}'.format(result=e.get_error_message())  
        else:
            return False  
      

    def setMaxVcpu(self,instance,cpu):
        # Adjust the number of CPUs
        if isinstance(cpu, int):
            try:
                flags = libvirt.VIR_DOMAIN_AFFECT_CONFIG + libvirt.VIR_DOMAIN_VCPU_MAXIMUM
                return instance.setVcpusFlags(cpu,flags)
                
            except libvirt.libvirtError,e:
                return 'Instance MAX CPU adjustment failed. Reasons for the failure:{result}'.format(result=e.get_error_message())  
        else:
            return False    

    #TEST BITISI  
    
    def setMem(self,instance,mem):
        '''Adjust memory size'''
        if isinstance(mem, int):
            mem = mem*1024
            try:
                return instance.setMemoryFlags(mem,flags=0)
            except libvirt.libvirtError,e:
                return 'Instance memory adjustment failed, Reason:{result}'.format(result=e.get_error_message())  
        else:
            return False

    # TEST BASLANGICI
    def setMaxMem(self,instance,mem):
        '''Adjust memory size'''
        if isinstance(mem, int):
            mem = mem*1024
            try:
                return instance.setMaxMemory(mem)
            except libvirt.libvirtError,e:
                return 'Instance memory adjustment failed, Reason:{result}'.format(result=e.get_error_message())  
        else:
            return False
    # TEST BITISI
    
    def migrate(self,instance,uri,dname,tcp_path):
        '''Virtual Machine Migration'''
        try:
            return instance.migrate(uri,True,dname,tcp_path,0) 
        except libvirt.libvirtError,e:
            return 'Instance migration failed, Reason:{result}'.format(result=e.get_error_message())        

    # TEST BASLANGICI
    def snapShotCreate(self,instance,snapName):
        '''Create an instance of all the disks for the instance'''
        try:
            snpXML = '''<domainsnapshot>
                            <name>{snapName}</name> 
                            <description>Snapshot of {snapName}</description>
                            <disks>
                            </disks>
                        </domainsnapshot>
            '''
            snpXML = snpXML.format(snapName=snapName)
            return instance.snapshotCreateXML(snpXML,0)
        except libvirt.libvirtError,e:    
            return 'Failed to create an instance disk snapshot, Reason:{result}'.format(result=e.get_error_message())  

    # TEST BITISI        
    
    def snapShotDelete(self,instance,snapName):
        '''Delete instance snapshot'''
        try:
            snap = instance.snapshotLookupByName(snapName)   
            return snap.delete()
        except libvirt.libvirtError,e:
            return 'Failed to delete the instance snapshot, Reason:{result}'.format(result=e.get_error_message())    
    
    def snapShotView(self,instance,snapName):
        '''View the instance snapshot'''
        try:
            snap = instance.snapshotLookupByName(snapName)  
            return snap.getXMLDesc()    
        except libvirt.libvirtError,e:
            return 'Failed to get an instance snapshot, Reason:{result}'.format(result=e.get_error_message())  

    def snapShotExists(self,instance,snapName):
        '''View if snapshot exists'''
        try:
            snap = instance.snapshotLookupByName(snapName)  
            return True
        except:
            return False
    
    def snapShotList(self,instance):
        '''List instance snapshots'''
        snapList = []
        try:
            for snap in instance.snapshotListNames():
                data = dict()
                data['name'] = snap
                snap = instance.snapshotLookupByName(snap)
                snapCtime = vMUtil.get_xml_path(snap.getXMLDesc(0), "/domainsnapshot/creationTime")
                data['last'] = snap.isCurrent()
                data['ctime'] = datetime.fromtimestamp(int(snapCtime))
                snapList.append(data)
        except:
            return snapList
        return snapList
    
    def revertSnapShot(self,instance,snapName):
        '''Snapshot recovery'''
        snap = instance.snapshotLookupByName(snapName)
        try:
            return instance.revertToSnapshot(snap,0)
        except libvirt.libvirtError,e:
            return 'Failed to restore the instance snapshot. Reason:{result}'.format(result=e.get_error_message())       
        
    def delete(self,instance):
        '''Delete the instance'''
        try:
            if instance.state()[0] == 5:
                return instance.undefineFlags()
            else:
                instance.undefineFlags()
                return instance.destroy() #执行成返回值为0
        except libvirt.libvirtError,e:
            return 'Instance deletion failed, Reason:{result}'.format(result=e.get_error_message())            
     
    def suspend(self,instance):  
        '''Suspend an instance'''
        try:
            return instance.suspend()
        except libvirt.libvirtError,e:
            return 'Failed to suspend instance, Reason:{result}'.format(result=e.get_error_message())           
        
    def resume(self,instance):
        '''Recovery instance'''
        try:
            return instance.resume()
        except libvirt.libvirtError,e:
            return 'Instance recovery failed, Reason:{result}'.format(result=e.get_error_message())       
        
    def reboot(self,instance):
        '''Restart the instance'''
        try:
            return instance.reboot()
        except libvirt.libvirtError,e:
            return 'Failed to restart the instance, Reason:{result}'.format(result=e.get_error_message())        
    
    def shutdown(self,instance):
        '''Close the instance'''
        try:
            return instance.shutdown()
        except libvirt.libvirtError,e:
            return 'Failed to close the instance, Reason:{result}'.format(result=e.get_error_message())         

    def destroy(self,instance):
        '''Forced shutdown of the instance'''
        try:
            return instance.destroy()
        except libvirt.libvirtError,e:
            return 'Instance forced shutdown failed, Reason:{result}'.format(result=e.get_error_message()) 
    
    def state(self,instance):
        '''Check the status of the instance'''
        try:
            return instance.state()
        except libvirt.libvirtError,e:
            return 'Failed to get instance status, failure reason:{result}'.format(result=e.get_error_message())   
            
    def start(self,instance):
        '''Start the instance'''
        try:
            return instance.create()
        except libvirt.libvirtError,e:
            return 'Instance startup failed, Reason:{result}'.format(result=e.get_error_message())     
        

class VMNetwork(VMBase):
    def __init__(self,conn):
        self.conn =  conn
     
    def defineXML(self, xml):
        '''Defining the incoming xml'''
        try:
            return self.conn.defineXML(xml)  
        except libvirt.libvirtError,e:
            return 'Network creation failed, Reason:{result}'.format(result=e.get_error_message())               
     
    def getNetwork(self,netk_name):
        '''Check if the network exists'''
        try:
            netk = self.conn.networkLookupByName(netk_name)
            return netk
        except libvirt.libvirtError:
            return False  
           
        
    def getNetworkType(self,netk_name):
        '''Get network type'''
        netk = self.getNetwork(netk_name)
        if netk:
            xml = netk.XMLDesc(0)
            tree = ElementTree.fromstring(xml)
            try:
                mode = tree.find('virtualport').get('type') 
            except:
                mode = 'brctl'
            model = tree.find('forward').get('mode')
            return {'mode':mode,'type': model}
        else:return False
        
    def getInterface(self, name):
        '''Get network interface'''
        try:
            return self.conn.interfaceLookupByName(name)
        except libvirt.libvirtError:
            return False

    def getInterfaceInfo(self, name):
        iface = self.getInterface(name)
        xml = iface.XMLDesc(0)
        mac = iface.MACString()
        itype = vMUtil.get_xml_path(xml, "/interface/@type")
        ipType = vMUtil.get_xml_path(xml, "/interface/protocol/@family")
        if ipType == 'ipv4':
            ipv4 = vMUtil.get_xml_path(xml, "/interface/protocol/ip/@address")
            mask = vMUtil.get_xml_path(xml, "/interface/protocol/ip/@prefix")
        else:
            ipv4 = None
            mask = None
        state = iface.isActive()
        return {'name': name, 'type': itype, 'state': state, 'mac': mac,'ipv4':ipv4,'mask':mask}
    
    def defineInterface(self, xml, flag=0):
        '''Define the network interface'''
        try:
            self.conn.interfaceDefineXML(xml, flag)
        except libvirt.libvirtError,e:
            return 'Failed to create network interface, Reason:{result}'.format(result=e.get_error_message())              

    def createBridgeInterface(self, iface,brName,ipaddr,mask,gateway,stp='on',delay=0):
        '''Create bridge type interface'''
        xml = """<interface type='bridge' name='{brName}'>
                    <start mode='onboot'/>""".format( brName=brName)
        if ipaddr and mask and gateway:
            xml += """ <protocol family='ipv4'>
                            <ip address='{ipaddr}' prefix='{mask}'/>
                            <route gateway="{gateway}"/>
                        </protocol>""".format(ipaddr=ipaddr,mask=mask,gateway=gateway)
        if stp:
            xml += """<bridge stp='{stp}' delay='{delay}'>
                            <interface name='{iface}' type='ethernet'/>
                          </bridge>""".format(stp=stp, delay=delay,iface=iface)
        xml += """</interface>"""
        try:
            self.defineInterface(xml)
            iface = self.getInterface(brName)
            return iface.create()    
        except libvirt.libvirtError,e:
            return 'Bridge NIC creation failed, Reason:{result}'.format(result=e.get_error_message())
        
    def stopInterface(self,iface):
        try:
            iface.destroy()
            return True
        except libvirt.libvirtError:
            return False

    def startInterface(self,iface):
        try:
            iface.create()
            return True
        except libvirt.libvirtError:
            return False

    def deleteInterface(self,iface):
        try:
            iface.destroy()
            return iface.undefine()
        except libvirt.libvirtError:
            return False
        
    def createNetwork(self,xml):
        '''Create network and set self-boot'''
        try:
            netk = self.conn.networkDefineXML(xml)
            netk.create()
            return netk.setAutostart(1)
        except libvirt.libvirtError,e:
            return 'Network creation failed, Reason:{result}'.format(result=e.get_error_message())             
        
    def deleteNetwork(self,netk):
        '''Delete network'''
        try:
            netk.destroy()
            return netk.undefine()
        except libvirt.libvirtError:
            return False  
        
        
    def listNetwork(self):
        '''List all networks'''
        dataList = []
        try:
            for netk in self.conn.listAllNetworks():         
                data = self.getNetworkType(netk.name())
                data['name'] = netk.name()
                data['alive'] = netk.isActive()
                data['pers'] = netk.isPersistent()
                dataList.append(data) 
        except libvirt.libvirtError:
            pass
        return dataList    
    
    def listInterface(self):
        '''List all interfaces'''
        dataList = []
        try:
            for ins in self.conn.listAllInterfaces():
                data = dict()
                data['name'] = ins.name()
                data['alive'] = ins.isActive()
                dataList.append(data) 
        except:
            pass
        return dataList                 

class LibvirtManage(object):
    def __init__(self, host, login=None, passwd=None, type=1,pool=True):
        self.login = login
        self.host = host
        self.passwd = passwd
        self.pool = pool
        self.type = type
        if self.pool:self.conn = connection_manager.get_connection(self.host, self.login, self.passwd, self.type)
        else:
            try:
                connect = soloConnection(self.host, self.login, self.passwd, self.type)
                self.conn = connect.connect()
            except libvirt.libvirtError:
                self.conn = False
        
    def genre(self,model):
        if model == 'storage':
            return VMStorage(conn=self.conn)
        elif model == 'instance':
            return VMInstance(conn=self.conn)
        elif model == 'server':
            return VMServer(conn=self.conn)
        elif model == 'network':
            return VMNetwork(conn=self.conn)            
        else:
            return False

        
    def close(self):
        if self.pool is False:self.conn.close()
        else:pass
        
        
if __name__ == '__main__':
    LIB = LibvirtManage('192.168.1.234', login=None, passwd=None, type=1,thread=False)
    server = LIB.genre(model='server')
    print server.getVmServerisAlive()
    print LIB.close()
