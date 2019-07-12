#!/usr/bin/env python
# _#_ coding:utf-8 _*_
import time
from django.http import JsonResponse
from django.shortcuts import render_to_response
from VManagePlatform.utils.vMConUtils import LibvirtManage
from VManagePlatform.models import VmServer,VmServerInstance,VmInstance_Template
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from VManagePlatform.const import Const
from VManagePlatform.utils.vConnUtils import CommTools
from VManagePlatform.tasks import migrateInstace,cloneInstace,recordLogs
from VManagePlatform.utils.vBrConfigUtils import BRManage
from django.contrib.auth.models import User
import spur
from VManagePlatform.views.vBackup import backupManager

@login_required
def addInstance(request,id):
    try:
        vmServer = VmServer.objects.get(id=id)
    except:
        return render_to_response('404.html',context_instance=RequestContext(request))
    if request.method == "GET":
        userList = User.objects.all()
        tempList = VmInstance_Template.objects.all()
        VMS = LibvirtManage(vmServer.server_ip,vmServer.username, vmServer.passwd,vmServer.vm_type)
        SERVER = VMS.genre(model='server')
        NETWORK = VMS.genre(model='network')
        if SERVER:vStorage = SERVER.getVmStorageInfo()
        vMImages =SERVER.getVmIsoList()
        netkList = NETWORK.listNetwork()
        VMS.close()
        return render_to_response('vmInstance/add_instance.html',
                                  {"user":request.user,"localtion":[{"name":"Home","url":'/'},{"name":"Virtual machine instance","url":"/allInstance"},
                                                                    {"name":"Add a virtual machine","url":'#'}],
                                    "vmServer":vmServer,"vStorage":vStorage,"vMImages":vMImages,"netkList":netkList,
                                    "tempList":tempList,"userList":userList},
                                  context_instance=RequestContext(request))
    elif request.method == "POST":
        op = request.POST.get('op')
        if op in ['custom','xml','template'] and request.user.has_perm('VManagePlatform.add_vmserverinstance'):
            VMS = LibvirtManage(vmServer.server_ip,vmServer.username, vmServer.passwd,vmServer.vm_type)
            INSTANCE = VMS.genre(model='instance')
            SERVER = VMS.genre(model='server')
            STORAGE = VMS.genre(model='storage')
            NETWORK = VMS.genre(model='network')

            if op == 'custom':
                netks = [ str(i) for i in request.POST.get('netk').split(',')]
                if INSTANCE:
                    instance =  INSTANCE.queryInstance(name=str(request.POST.get('vm_name')))
                    if instance:
                        return  JsonResponse({"code":500,"msg":"The virtual machine already exists","data":None})
                    else:

                        networkXml = ''
                        radStr = CommTools.radString(4)
                        for nt in netks:
                            netkType = NETWORK.getNetworkType(nt)
                            netXml = Const.CreateNetcard(nkt_br=nt,ntk_name=nt+'-'+radStr,data=netkType)
                            networkXml = netXml +  networkXml
                        pool = STORAGE.getStoragePool(pool_name=request.POST.get('storage'))
                        volume_name = request.POST.get('vm_name')+'.img'
                        if pool:
                            volume = STORAGE.createVolumes(pool, volume_name=volume_name, volume_capacity=request.POST.get('disk'))

                            if isinstance(volume, str):return JsonResponse({"code":500,"msg":volume,"data":None})
                            else:
                                disk_path = volume.path()
                                volume_name = volume.name()
                                disk_xml = Const.CreateDisk(volume_path=disk_path)
                        else:
                            return  jsonResponse({"code":500,"msg":"Failed to add virtual machine and the storage pool has been deleted","data":None})
                        dom_xml = Const.CreateIntanceConfig(dom_name=request.POST.get('vm_name'),maxMem=int(SERVER.getServerInfo().get('mem')),
                                                      mem=int(request.POST.get('mem')),cpu=request.POST.get('cpu'),disk=disk_xml,
                                                      iso_path=request.POST.get('system'),network=networkXml)

                        dom = SERVER.createInstance(dom_xml)

                        if dom==0:
                            instance = INSTANCE.queryInstance(name=str(request.POST.get('vm_name')))
                            vm_info = INSTANCE.getVmInstanceInfo(instance,vmServer.server_ip,str(request.POST.get('vm_name')))
                            vm_vnc_port = vm_info.get('vnc')
                            vm_token = vm_info.get('token')
                            VMS.close()
                            try:
                                VmServerInstance.objects.create(server=vmServer,name=request.POST.get('vm_name'),mem=int(request.POST.get('mem')),status=1,
                                                                cpu=request.POST.get('cpu'),token=vm_token)
                            except Exception,e:
                                return  JsonResponse({"code":500,"data":None,"msg":e})

                            recordLogs(server_id=vmServer.id,vm_name=request.POST.get('vm_name'),
                                             content="Create a virtual machine{name}".format(name=request.POST.get('vm_name')),
                                             user=str(request.user),status=dom)


                            return JsonResponse({"code":200,"data":[vm_vnc_port,vm_token],"msg":"The virtual host was added successfully."})
                        else:

                            STORAGE.deleteVolume(pool, volume_name)
                            VMS.close()

                            recordLogs(server_id=vmServer.id,vm_name=request.POST.get('vm_name'),
                                             content="Create a virtual machine{name}".format(name=request.POST.get('vm_name')),
                                             user=str(request.user),status=1,result=dom)

                            return JsonResponse({"code":500,"data":None,"msg":dom})


            elif op == 'xml':
                domXml = request.POST.get('xml')
                dom = SERVER.defineXML(xml=domXml)
                VMS.close()
                if isinstance(dom,int):
                    recordLogs.delay(server_id=vmServer.id,vm_name=request.POST.get('vm_name'),
                                             content="Create a virtual machine through XML{name}".format(name=request.POST.get('vm_name')),
                                             user=str(request.user),status=dom)
                    return  JsonResponse({"code":200,"data":None,"msg":"The virtual host was added successfully."})
                else:
                    recordLogs.delay(server_id=vmServer.id,vm_name=request.POST.get('vm_name'),
                                             content="Create a virtual machine through XML{name}".format(name=request.POST.get('vm_name')),
                                             user=str(request.user),status=1,result=dom)
                    return JsonResponse({"code":500,"data":None,"msg":dom})
            elif op=='template':
                try:
                    temp = VmInstance_Template.objects.get(id=request.POST.get('temp'))
                    if INSTANCE:instance =  INSTANCE.queryInstance(name=str(request.POST.get('vm_name')))
                    if instance:return  JsonResponse({"code":500,"msg":"The virtual machine already exists","data":None})
                    else:
                        pool = STORAGE.getStoragePool(pool_name=request.POST.get('storage'))
                        volume_name = request.POST.get('vm_name')+'.img'
                        if pool:
                            volume = STORAGE.createVolumes(pool, volume_name=volume_name, volume_capacity=temp.disk)
                            if volume:
                                disk_path = volume.path()
                                volume_name = volume.name()
                                disk_xml = Const.CreateDisk(volume_path=disk_path)
                            else:return JsonResponse({"code":500,"msg":"Failed to add a virtual machine. The disk named in the host name exists in the storage pool.","data":None})
                        else:
                            return  JsonResponse({"code":500,"msg":"Failed to add virtual machine and the storage pool has been deleted","data":None})
                        dom_xml = Const.CreateIntanceConfig(dom_name=request.POST.get('vm_name'),maxMem=int(SERVER.getServerInfo().get('mem')),
                                                      mem=temp.mem,cpu=temp.cpu,disk=disk_xml,
                                                      iso_path=request.POST.get('system'),network=None)
                        dom = SERVER.createInstance(dom_xml)
                        if dom==0:
                            VMS.close()
                            recordLogs.delay(server_id=vmServer.id,vm_name=request.POST.get('vm_name'),
                                             content="Create a virtual machine from a template{name}".format(name=request.POST.get('vm_name')),
                                             user=str(request.user),status=dom)
                            return JsonResponse({"code":200,"data":None,"msg":"The virtual host was added successfully."})
                        else:
                            STORAGE.deleteVolume(pool, volume_name)
                            VMS.close()
                            recordLogs.delay(server_id=vmServer.id,vm_name=request.POST.get('vm_name'),
                                             content="Create a virtual machine from a template{name}".format(name=request.POST.get('vm_name')),
                                             user=str(request.user),status=1,result=dom)
                            return JsonResponse({"code":500,"data":None,"msg":dom})
                except:
                    return JsonResponse({"code":500,"data":None,"msg":"Failed to add virtual host."})

        else:return JsonResponse({"code":500,"data":None,"msg":"Unsupported action or you do not have permission to add a virtual machine"})

@login_required
def modfInstance(request,id):
    try:
        vServer = VmServer.objects.get(id=id)
    except Exception,e:
        return JsonResponse({"code":500,"msg":"Host resource not found","data":e})
    if request.method == "POST":
        if CommTools.argsCkeck(args=['op','server_id','vm_name'], data=request.POST) and request.user.has_perm('VManagePlatform.change_vmserverinstance'):
            LIBMG = LibvirtManage(vServer.server_ip,vServer.username, vServer.passwd,vServer.vm_type)
            SERVER = LIBMG.genre(model='server')
            STORAGE = LIBMG.genre(model='storage')
            INSTANCE = LIBMG.genre(model='instance')
            if SERVER:
                instance = INSTANCE.queryInstance(name=str(request.POST.get('vm_name')))
                if instance is False:
                    LIBMG.close()
                    return  JsonResponse({"code":404,"data":None,"msg":"The virtual machine does not exist or has been deleted."})
            else:return  JsonResponse({"code":500,"data":None,"msg":"Virtual host link failed."})

            if request.POST.get('device') == 'disk':
                if request.POST.get('op') == 'attach':
                    if instance.state()[0] == 5:return  JsonResponse({"code":500,"data":None,"msg":"Please start the virtual machine first."})
                    storage = STORAGE.getStoragePool(pool_name=request.POST.get('pool_name'))
                    if storage:
                        volume = STORAGE.createVolumes(pool=storage, volume_name=request.POST.get('vol_name'),
                                                       drive=request.POST.get('vol_drive'), volume_capacity=request.POST.get('vol_size'))
                        if volume:
                            volPath = volume.path()
                            volume_name = volume.name()
                        else:
                            LIBMG.close()
                            return  JsonResponse({"code":500,"data":None,"msg":"The volume already exists."})
                        status = INSTANCE.addInstanceDisk(instance, volPath)
                        LIBMG.close()
                        if isinstance(status,int):
                            recordLogs.delay(server_id=vServer.id,vm_name=request.POST.get('vm_name'),
                                             content="virtual machine{name},Add to{size}GB hard disk{volume_name}".format(name=request.POST.get('vm_name'),
                                                                                           volume_name=request.POST.get('vol_name'),
                                                                                           size=request.POST.get('vol_size')),
                                             user=str(request.user),status=0)
                            return  JsonResponse({"code":200,"data":None,"msg":"Successful operation。"})
                        else:
                            recordLogs.delay(server_id=vServer.id,vm_name=request.POST.get('vm_name'),
                                             content="virtual machine{name},Add to{size}GB hard disk{volume_name}".format(name=request.POST.get('vm_name'),
                                                                                                    volume_name=request.POST.get('vol_name'),
                                                                                                    size=request.POST.get('vol_size')),
                                             user=str(request.user),status=1,result=status)
                            return  JsonResponse({"code":500,"data":status,"msg":status})
                    else:
                        LIBMG.close()
                        return  JsonResponse({"code":404,"data":None,"msg":"The storage pool does not exist or has been deleted."})
                elif  request.POST.get('op') == 'detach':
                    status = INSTANCE.delInstanceDisk(instance, volPath=request.POST.get('disk'))
                    LIBMG.close()
                    if isinstance(status,int):
                        recordLogs.delay(server_id=vServer.id,vm_name=request.POST.get('vm_name'),
                                             content="virtual machine{name},Delete the hard disk{volume_name}".format(name=request.POST.get('vm_name'),volume_name=request.POST.get('volPath')),
                                             user=str(request.user),status=0)
                        return  JsonResponse({"code":200,"data":None,"msg":"Successful operation。"})
                    else:
                        LIBMG.close()
                        recordLogs.delay(server_id=vServer.id,vm_name=request.POST.get('vm_name'),
                                             content="virtual machine{name},Delete the hard disk{volume_name}".format(name=request.POST.get('vm_name'),volume_name=request.POST.get('volPath')),
                                             user=str(request.user),status=1,result=status)
                        return  JsonResponse({"code":500,"data":status,"msg":status})

            elif  request.POST.get('device') == 'netk':
                if request.POST.get('op') == 'attach':
                    result = INSTANCE.addInstanceInterface(instance, brName=request.POST.get('netk_name'))
                    if isinstance(result,int):
                        recordLogs.delay(server_id=vServer.id,vm_name=request.POST.get('vm_name'),
                                         content="virtual machine{name}Add network card".format(name=request.POST.get('vm_name')),
                                         user=str(request.user),status=0)
                        return  JsonResponse({"code":200,"data":None,"msg":"Successful operation。"})
                    else:
                        recordLogs.delay(server_id=vServer.id,vm_name=request.POST.get('vm_name'),
                                         content="virtual machine{name}Add network card".format(name=request.POST.get('vm_name')),
                                         user=str(request.user),status=1,result=result)
                        return  JsonResponse({"code":500,"data":result,"msg":result})
                elif  request.POST.get('op') == 'detach':
                    result = INSTANCE.delInstanceInterface(instance, interName=request.POST.get('netk'))
                    if isinstance(result,int):
                        recordLogs.delay(server_id=vServer.id,vm_name=request.POST.get('vm_name'),
                                         content="virtual machine{name}Delete network card".format(name=request.POST.get('vm_name')),
                                         user=str(request.user),status=0)
                        return  JsonResponse({"code":200,"data":None,"msg":"Successful operation。"})
                    else:
                        recordLogs.delay(server_id=vServer.id,vm_name=request.POST.get('vm_name'),
                                         content="virtual machine{name}Delete network card".format(name=request.POST.get('vm_name')),
                                         user=str(request.user),status=1,result=result)
                        return  JsonResponse({"code":500,"data":None,"msg":result})

            #Adjust the size of MEMORY
            elif  request.POST.get('device') == 'mem':
                if request.POST.get('op') == 'attach':
                    result = INSTANCE.setMem(instance, mem=int(request.POST.get('mem')))
                    LIBMG.close()
                    if isinstance(result,int):
                        recordLogs(server_id=vServer.id,vm_name=request.POST.get('vm_name'),
                                    content="virtual machine {name} Adjust memory for {size} MB".format(name=request.POST.get('vm_name'),
                                    size=request.POST.get('mem')), user=str(request.user),status=0, result='SUCCESSFUL')
                        return  JsonResponse({"code":200,"data":None,"msg":"Successful operation。"})
                    else:
                        recordLogs(server_id=vServer.id,vm_name=request.POST.get('vm_name'),
                                    content="virtual machine {name} A djust memory for {size} MB".format(name=request.POST.get('vm_name'),
                                    size=request.POST.get('mem')), user=str(request.user),status=1 , result=result)
                        return  JsonResponse({"code":500,"data":None,"msg":result})

            #Adjust the size of MAXIMUM MEMORY
            elif  request.POST.get('device') == 'max_mem':
                if request.POST.get('op') == 'attach':
                    result = INSTANCE.setMaxMem(instance, mem=int(request.POST.get('max_mem')))
                    LIBMG.close()
                    if isinstance(result,int):
                        recordLogs(server_id=vServer.id,vm_name=request.POST.get('vm_name'),
                                    content="virtual machine {name} Adjust maximum memory for {size} MB".format(name=request.POST.get('vm_name'),
                                    size=request.POST.get('mem')), user=str(request.user),status=0, result='SUCCESSFUL')
                        return  JsonResponse({"code":200,"data":None,"msg":"Successful operation。"})
                    else:
                        recordLogs(server_id=vServer.id,vm_name=request.POST.get('vm_name'),
                                    content="virtual machine {name} Adjust maximum memory for {size} MB".format(name=request.POST.get('vm_name'),
                                    size=request.POST.get('mem')), user=str(request.user),status=1 , result=result)
                        return  JsonResponse({"code":500,"data":None,"msg":result})

            #Adjust the number of CPU
            elif  request.POST.get('device') == 'cpu':
                if request.POST.get('op') == 'attach':



                    result = INSTANCE.setVcpu(instance, cpu=int(request.POST.get('cpu')))
                    LIBMG.close()
                    if isinstance(result,int):
                        recordLogs(server_id=vServer.id,vm_name=request.POST.get('vm_name'),
                                    content="virtual machine {name} Adjust the CPU to {size} ".format(name=request.POST.get('vm_name'), size=request.POST.get('cpu')),
                                    user=str(request.user),status=0, result='SUCCESSFUL')

                        return  JsonResponse({"code":200,"data":None,"msg":"Successful operation。"})

                    else:
                        recordLogs(server_id=vServer.id,vm_name=request.POST.get('vm_name'),
                                    content="virtual machine {name} Adjust the CPU to {size} ".format(name=request.POST.get('vm_name'), size=request.POST.get('cpu')),
                                    user=str(request.user),status=1, result=result)
                        return  JsonResponse({"code":500,"data":None,"msg":result})

            #Adjust the number of CPU
            elif  request.POST.get('device') == 'max_cpu':
                if request.POST.get('op') == 'attach':

                    result = INSTANCE.setMaxVcpu(instance, cpu=int(request.POST.get('max_cpu')))
                    LIBMG.close()
                    if isinstance(result,int):
                        recordLogs(server_id=vServer.id,vm_name=request.POST.get('vm_name'),
                                    content="virtual machine {name} Adjust the CPU to {size} ".format(name=request.POST.get('vm_name'), size=request.POST.get('max_cpu')),
                                    user=str(request.user),status=0, result='SUCCESSFUL')

                        return  JsonResponse({"code":200,"data":None,"msg":"Successful operation。"})

                    else:
                        recordLogs(server_id=vServer.id,vm_name=request.POST.get('vm_name'),
                                    content="virtual machine {name} Adjust the CPU to {size} ".format(name=request.POST.get('vm_name'), size=request.POST.get('max_cpu')),
                                    user=str(request.user),status=1, result=result)
                        return  JsonResponse({"code":500,"data":None,"msg":result})

            elif  request.POST.get('device') == 'bandwidth':
                SSH = BRManage(hostname=vServer.server_ip,port=22)
                OVS = SSH.genre(model='ovs')
                mode = INSTANCE.getInterFace(instance,request.POST.get('netk_name'))
                if request.POST.get('op') == 'attach':
                    if mode.get('type') == 'openvswitch':
                        if int(request.POST.get('bandwidth')) == 0:result = OVS.ovsCleanBandwidth(port=request.POST.get('netk_name'))
                        else:result = OVS.ovsConfBandwidth(port=request.POST.get('netk_name'), bandwidth=request.POST.get('bandwidth'))
                    else:
                        if int(request.POST.get('bandwidth')) == 0:result = INSTANCE.cleanInterfaceBandwidth(instance, request.POST.get('netk_name'))
                        result = INSTANCE.setInterfaceBandwidth(instance, port=request.POST.get('netk_name'), bandwidth=request.POST.get('bandwidth'))
                    SSH.close()
                    LIBMG.close()
                    if result.get('status') == 'success':
                        recordLogs.delay(server_id=vServer.id,vm_name=request.POST.get('vm_name'),
                                         content="virtual machine{name}, Adjust the bandwidth to:{bandwidth}Mbps".format(name=request.POST.get('vm_name'), bandwidth=request.POST.get('bandwidth')),
                                         user=str(request.user),status=0)
                        return  JsonResponse({"code":200,"data":None,"msg":"Successful operation。"})
                    else:return  JsonResponse({"code":500,"data":None,"msg":"No bandwidth set, no need to clear"})

            elif  request.POST.get('device') == 'cdrom':
                if request.POST.get('op') == 'attach':
                    result = INSTANCE.addInstanceCdrom(instance, isoPath=request.POST.get('iso_path'))
                    if isinstance(result,str):
                        recordLogs.delay(server_id=vServer.id,vm_name=request.POST.get('vm_name'),
                                         content="virtual machine{name}Add optical drive{iso_path}Success".format(name=request.POST.get('vm_name'),
                                                                            iso_path=request.POST.get('iso_path').split('/')[-1]),
                                         user=str(request.user),status=1)
                        return  JsonResponse({"code":500,"data":None,"msg":result})
                    elif isinstance(result,int) or isinstance(result,object):
                        recordLogs.delay(server_id=vServer.id,vm_name=request.POST.get('vm_name'),
                                         content="virtual machine{name}Add optical drive{iso_path}Success".format(name=request.POST.get('vm_name'),
                                                                                 iso_path=request.POST.get('iso_path').split('/')[-1]),
                                         user=str(request.user),status=0)
                        return  JsonResponse({"code":200,"data":None,"msg":"Add the optical drive successfully and restart the virtual machine to take effect."})
                elif  request.POST.get('op') == 'detach':
                    status = INSTANCE.delInstanceCdrom(instance, cdrom=request.POST.get('cdrom'))
                    LIBMG.close()
                    if isinstance(status,str):
                        recordLogs.delay(server_id=vServer.id,vm_name=request.POST.get('vm_name'),
                                             content="virtual machine{name}, remove the optical drive{cdrom}".format(name=request.POST.get('vm_name'),cdrom=request.POST.get('cdrom')),
                                             user=str(request.user),status=1,result=status)
                        return  JsonResponse({"code":200,"data":status,"msg":status})
                    elif isinstance(status,int) or isinstance(status,object):
                        recordLogs.delay(server_id=vServer.id,vm_name=request.POST.get('vm_name'),
                                             content="virtual machine{name}, remove the optical drive{cdrom}".format(name=request.POST.get('vm_name'),cdrom=request.POST.get('cdrom')),
                                             user=str(request.user),status=0)
                        return  JsonResponse({"code":200,"data":None,"msg":"Delete the optical drive successfully and restart the virtual machine to take effect."})

            LIBMG.close()
        else:
            return  JsonResponse({"code":500,"data":None,"msg":"An operation that is not currently supported or you do not have permission to operate this item."})
@login_required
def handleInstance(request,id):
    try:
        vServer = VmServer.objects.get(id=id)
    except Exception,e:
        return JsonResponse({"code":500,"msg":"Host resource not found","data":e})
    if request.method == "POST":
        op = request.POST.get('op')
        insName = request.POST.get('vm_name')
        if op in ['start','reboot','shutdown','halt','suspend',
                  'resume','xml','migrate','delete','mount',
                  'umount','clone'] and request.user.has_perm('VManagePlatform.change_vmserverinstance'):
            try:
                VMS = LibvirtManage(vServer.server_ip,vServer.username, vServer.passwd,vServer.vm_type)
            except Exception,e:
                return  JsonResponse({"code":500,"msg":"The server connection failed. .","data":e})
            try:
                INSTANCE = VMS.genre(model='instance')
                instance = INSTANCE.queryInstance(name=str(insName))
            except Exception,e:
                return JsonResponse({"code":500,"msg":"The forced shutdown of the virtual machine failed. .","data":e})
            if op == 'halt':
                result = INSTANCE.destroy(instance)
                content = "Shut down the virtual machine {name}".format(name=insName)
            elif op == 'start':
                result = INSTANCE.start(instance)
                content = "Start the virtual machine {name}".format(name=insName)
            elif op == 'reboot':
                result = INSTANCE.reboot(instance)
                content = "Restart the virtual machine {name}".format(name=insName)
            elif op == 'shutdown':
                result = INSTANCE.shutdown(instance)
                content = "Shut down the virtual machine {name}".format(name=insName)
            elif op == 'suspend':
                result = INSTANCE.suspend(instance)
                content = "Suspend virtual machine {name}".format(name=insName)
            elif op == 'resume':
                result = INSTANCE.resume(instance)
                content = "Recover virtual machines {name}".format(name=insName)
            elif op == 'delete':
                INSTANCE.delDisk(instance)
                VmServerInstance.objects.get(token=INSTANCE.getInsUUID(instance)).delete()
                result = INSTANCE.delete(instance)
                content = "Delete virtual machine {name}".format(name=insName)
            elif op == 'migrate':
                migrateInstace.delay(request.POST,str(request.user))
                VMS.close()
                return  JsonResponse({"code":200,"data":None,"msg":"Migration task submitted successfully."})
            elif op == 'umount':
                result = INSTANCE.umountIso(instance, dev=request.POST.get('dev'), image=request.POST.get('iso'))
                content = "Uninstall the optical drive {name}".format(name=insName)
            elif op == 'mount':
                result = INSTANCE.mountIso(instance, dev=request.POST.get('dev'), image=request.POST.get('iso'))
                content = "Mount optical drive {name}".format(name=insName)
            elif op == 'clone':
                cloneInstace.delay(data=request.POST,user=str(request.user))
                VMS.close()
                return  JsonResponse({"code":200,"data":None,"msg":"Clone task submitted successfully."})
            elif op == 'xml':
                result = INSTANCE.defineXML(xml=request.POST.get('xml'))
                content = "Modify the instance through xml {name}".format(name=insName)
                return  JsonResponse({"code":200,"data":None,"msg":content})
            VMS.close()

            if isinstance(result,int) : #or isinstance(result,object):
                recordLogs(server_id=vServer.id,vm_name=insName,content=content,user=str(request.user),status=0,result="SUCCESSFUL")
                return  JsonResponse({"code":200,"data":None,"msg":"Successful operation。"})
            else:
                recordLogs(server_id=vServer.id,vm_name=insName,content=content,user=str(request.user),status=1,result=result)
                return  JsonResponse({"code":500,"data":result,"msg":result})

        else:
            return  JsonResponse({"code":500,"data":None,"msg":"Unsupported operation or you do not have permission to operate this item."})

    else:
        return  JsonResponse({"code":500,"data":None,"msg":"Unsupported HTTP operations"})

@login_required
def listInstance(request,id):
    if request.method == "GET":
        try:
            vServer = VmServer.objects.get(id=id)
        except:
            return render_to_response('404.html',context_instance=RequestContext(request))
        try:
            VMS = LibvirtManage(vServer.server_ip,vServer.username, vServer.passwd, vServer.vm_type)
            SERVER = VMS.genre(model='server')
            VMS.close()
            userList = User.objects.all()
            if SERVER:
                inStanceList = SERVER.getVmInstanceBaseInfo(server_ip=vServer.server_ip,server_id=vServer.id)
                VMS.close()
            else:return render_to_response('404.html',context_instance=RequestContext(request))
        except:
            inStanceList = None
        return render_to_response('vmInstance/list_instance.html',
                                  {"user":request.user,"localtion":[{"name":"Home","url":'/'},{"name":"Virtual machine instance","url":'#'},
                                                                    {"name":"List of virtual machine instances","url":"/listInstance/%d/" % vServer.id}],
                                   "inStanceList":inStanceList,"vmServer":vServer,"userList":userList},
                                  context_instance=RequestContext(request))

@login_required
def viewInstance(request,id,vm):
    if request.method == "GET":
        vmServer = VmServer.objects.get(id=id)
        serverList = VmServer.objects.all().order_by("-id")
        instance = None
        poolInfo = None
        netkInfo = None
        imgList = None
        isoList = None
        insXml = None
        insInfo = dict()
        kkk = []
        backupList = None

        try:
            VMS = LibvirtManage(vmServer.server_ip,vmServer.username, vmServer.passwd, vmServer.vm_type)
            INSTANCE = VMS.genre(model='instance')
            SERVER = VMS.genre(model='server')
            NETWORK = VMS.genre(model='network')

            if INSTANCE:
                instance = INSTANCE.queryInstance(name=str(vm))
                '''Get storage pool'''
                poolInfo = SERVER.getVmStorageInfo()
                '''Get network equipment'''
                netkInfo = NETWORK.listNetwork()
                '''Get cdrom device'''
                imgList =  INSTANCE.getMediaDevice(instance)
                '''Get iso list of iso storage pool'''
                isoList = SERVER.getVmIsoList()
                '''Get the instance's xml file'''
                insXml = INSTANCE.getInsXMLDesc(instance, flag=0)
                '''Get instance information'''
                insInfo = INSTANCE.getVmInstanceInfo(instance,server_ip=vmServer.server_ip,vMname=vm)
                insInfo['cpu_per'] = INSTANCE.getCpuUsage(instance)

                #TEST  IP BOS ISE VERITABANINDAN IP DEGERINI AL
                if not insInfo['ip']:
                    kkk = VmServerInstance.objects.get(name=str(insInfo['name']))
                    insInfo['eth0_ip'] = kkk.ips

                #  Ornek SSH Baglantisi
                '''
                try:
                    #sshHost = backupManager(vmServer.id, vmServer.hostname,vmServer.username, vmServer.passwd)
                    #bbb = sshHost.listVmBackup(vmName=str(insInfo['name']))
                    #backupList = sshHost.listVmBackup(vmName=str(insInfo['name']))       #bbb.split()
                    #result = insInfo['name']
                    #result = sshHost.result


                    shell = spur.SshShell(hostname=vmServer.server_ip, username="root", password=vmServer.passwd)
                    with shell:
                        #result = shell.run(["echo", "-n", "hello"])
                        ssh_response = shell.run(["uname", "-a"])
                except:
                    ssh_response = "SSH connection error."
                    pass
                insInfo['ssh_response'] = ssh_response.output

                '''
                # Ornek SSH Baglantisi BITISI

                snapList = INSTANCE.snapShotList(instance)
                VMS.close()
            else:return render_to_response('404.html',context_instance=RequestContext(request))
        except Exception,e:
            snapList = None

            #HOST SUNUCUYA ERISILEMIYOR ISE VERITABANINDAN BILGILERI  AL
            kkk = VmServerInstance.objects.get(name=vm, server_id=vmServer.id)
            insInfo['name'] = kkk.name
            insInfo['ip'] = kkk.ips
            insInfo['cpu'] = kkk.cpu
            insInfo['mem'] = kkk.mem
            insInfo['status'] = kkk.status

            pass

        return render_to_response('vmInstance/view_instance.html',
                                  {"user":request.user,"localtion":[{"name":"Home","url":'/'}, {"name":"List of virtual machine instances","url":"/allInstance"},
                                  {"name":"%s VM Details" % str(vm),"url":"/viewInstance/%d/%s/" % (int(id), str(vm))}],
                                   "inStance":insInfo,"vmServer":vmServer,"snapList":snapList,"poolInfo":poolInfo,
                                   "netkInfo":netkInfo,"imgList":imgList,"isoList":isoList,"serverList":serverList,
                                   "insXml":insXml, "backupList":backupList},
                                  context_instance=RequestContext(request))

@login_required
def tempInstance(request):
    if request.method == "GET":
        tempList = VmInstance_Template.objects.all()
        return render_to_response('vmInstance/temp_instance.html',
                                  {"user":request.user,"localtion":[{"name":"Home","url":'/'},{"name":"Instance template","url":'/tempInstance'}],
                                   "tempList":tempList},
                                  context_instance=RequestContext(request))
    elif request.method == "POST":
        op = request.POST.get('op')
        if op in ['add','modf','del'] and request.user.has_perm('VManagePlatform.add_vminstance_template'):
            if op == 'add':
                result = VmInstance_Template.objects.create(name=request.POST.get('name'),cpu=request.POST.get('cpu'),
                                                       mem=request.POST.get('mem'),disk=request.POST.get('disk'))
                if isinstance(result, str):return JsonResponse({"code":500,"data":result,"msg":"添加失败。"})
                else:return JsonResponse({"code":200,"data":None,"msg":"Added successfully."})
        else:return JsonResponse({"code":500,"data":None,"msg":"Unsupported operation or you do not have permission to operate this item."})

@login_required
def instanceCpuStatus(request,id,vm):
    """
    Return instance cpu usage
    """
    vmServer = VmServer.objects.get(id=id)
    try:
        VMS = LibvirtManage(vmServer.server_ip,vmServer.username, vmServer.passwd, vmServer.vm_type)
        INSTANCE = VMS.genre(model='instance')
        instance = INSTANCE.queryInstance(name=str(vm))
        data = dict()
        data['ctime'] = time.strftime('%Y-%m-%d %H:%M:%S' ,time.localtime())
        data['per'] = INSTANCE.getCpuUsage(instance)#random.randint(50,100)
        return JsonResponse({"code":200,"data":data,"msg":None}) #
    except Exception,e:
        return JsonResponse({"code":200,"data":{'ctime':time.strftime('%Y-%m-%d %H:%M:%S' ,time.localtime()),"per":0},"msg":None})


@login_required
def instanceNetStatus(request,id,vm):
    """
    Return instance network flow usage
    """
    vmServer = VmServer.objects.get(id=id)
    try:
        VMS = LibvirtManage(vmServer.server_ip,vmServer.username, vmServer.passwd, vmServer.vm_type)
        INSTANCE = VMS.genre(model='instance')
        instance = INSTANCE.queryInstance(name=str(vm))
        netFlow = INSTANCE.getNetUsage(instance)
        rx = 0
        tx = 0
        for dev in netFlow:
            rx += dev.get('rx')
            tx += dev.get('tx')
        data = dict()
        data['ctime'] = time.strftime('%Y-%m-%d %H:%M:%S' ,time.localtime())
        data['net'] = {'in':int(tx/1024)/1024,'out':int(rx/1024)/1024}#{'in':random.randint(50,100),'out':random.randint(50,100)}
        return JsonResponse({"code":200,"data":data,"msg":None}) #
    except Exception,e:
        return JsonResponse({"code":200,"data":{'ctime':time.strftime('%Y-%m-%d %H:%M:%S' ,time.localtime()),"net":{"rt":0,"tx":0}},"msg":str(e)})


@login_required
def instanceDiskStatus(request,id,vm):
    """
    Return instance disk usage
    """
    vmServer = VmServer.objects.get(id=id)
    try:
        VMS = LibvirtManage(vmServer.server_ip,vmServer.username, vmServer.passwd, vmServer.vm_type)
        INSTANCE = VMS.genre(model='instance')
        instance = INSTANCE.queryInstance(name=str(vm))
        diskUsage = INSTANCE.getDiskUsage(instance)
        rd = 0
        wr = 0
        for dev in diskUsage:
            rd += dev.get('rd')
            wr += dev.get('wr')
        data = dict()
        data['ctime'] = time.strftime('%Y-%m-%d %H:%M:%S' ,time.localtime())
        data['disk'] = {'rd':int(rd/1024)/1024,'wr':int(wr/1024)/1024}#{'in':random.randint(50,100),'out':random.randint(50,100)}
        return JsonResponse({"code":200,"data":data,"msg":None}) #
    except Exception,e:
        return JsonResponse({"code":200,"data":{'ctime':time.strftime('%Y-%m-%d %H:%M:%S' ,time.localtime()),"disk":{"rd":0,"wr":0}},"msg":str(e)})
