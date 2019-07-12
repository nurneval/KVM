#!/usqr/bin/env python
# _#_ coding:utf-8 _*_
from django.http import JsonResponse
from django.shortcuts import render_to_response
from VManagePlatform.utils.vMConUtils import LibvirtManage
from VManagePlatform.models import VmServer, VmServerInstance
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.contrib.auth.decorators import permission_required

from django.contrib.auth.models import User

@login_required
def listVmServer(request):
    ''' Host'larin CPU,RAM,INSTANCE, STATUS degerleri dogru alinamadigindan yeniden yazilmis ve hatalar giderilmistir 2018-07-19 '''
    hostList = VmServer.objects.all().order_by("-id")
    count = 0
    hostsInfo = []
    for host in hostList:
        try:
            hostConn = LibvirtManage(host.server_ip,host.username, host.passwd, host.vm_type)
            hostSrv = hostConn.genre(model='server')
            hostConn.close()
            hostInfo = hostSrv.getVmServerInfo()

            hostsInfo+={'status': hostInfo['status']},
            hostsInfo[count]['hostname'] = host.hostname
            hostsInfo[count]['server_ip'] = host.server_ip
            hostsInfo[count]['id'] = host.id

            hostsInfo[count]['cpu_total'] = hostInfo['cpu_total']
            hostsInfo[count]['mem'] = hostInfo['mem']
            hostsInfo[count]['instance'] = sum([len(v) for v in hostInfo['vmStatus'].values()])

            count+=1

        except:
            hostsInfo+={'status': 1},
            hostsInfo[count]['hostname'] = host.hostname
            hostsInfo[count]['server_ip'] = host.server_ip
            hostsInfo[count]['id'] = host.id

            hostsInfo[count]['cpu_total'] = host.cpu_total
            hostsInfo[count]['mem'] = host.mem
            hostsInfo[count]['instance'] = host.instance
            count+=1
            continue

    return render_to_response('vmServer/list_server.html',
                                  {"user":request.user,"localtion":[{"name":"Home","url":'/'},{"name":"Host List","url":"/listServer"}],
                                   "hostsInfo":hostsInfo,"model":"server"},
                                  context_instance=RequestContext(request))


@login_required
@permission_required('VManagePlatform.read_vmserver',login_url='/noperm/')
def viewVmServer(request,id):
    try:
        vServer = VmServer.objects.get(id=id)
    except:
        return render_to_response('404.html',context_instance=RequestContext(request))

    ''' Kapali Host'a uygulamadan erisilmek istendiginde program kiriliyordu. Alttaki Host'a baglanirken try/except eklenmistir 2018-07-19'''
    try:
        VMS = LibvirtManage(vServer.server_ip,vServer.username, vServer.passwd, vServer.vm_type)
        SERVER = VMS.genre(model='server')
        vmServer =  SERVER.getVmServerInfo()
    except:
        return render_to_response('404.html',context_instance=RequestContext(request))
    if vmServer:
        vmServer['id'] = vServer.id
        vmServer['server_ip'] = vServer.server_ip
        vmServer['name'] = vServer.hostname
        vmServer['mem'] = vmServer['mem'] / 1024 #GB Convertion
    vmStorage = SERVER.getVmStorageInfo()
    vmInstance = SERVER.getVmInstanceInfo(server_ip=vServer.server_ip)
    vmIns = vmInstance.get('active').get('number') + vmInstance.get('inactice').get('number')
    vmInsList = []
    for vm in vmIns:
        vm['netk'] = ','.join(vm.get('netk'))
        vm['disk'] = vm.get('disks')
        vm.pop('disks')
        vmInsList.append(vm)
    VMS.close()
    return render_to_response('vmServer/index_server.html',
                                  {"user":request.user,"localtion":[{"name":"Home","url":'/'},{"name":"Virtual Machine Manager","url":'#'},{"name":"Host list","url":"/listServer"},
                                                                    {"name":vmServer.get('name'),"url":"/viewServer/%d/" % vServer.id}],
                                   "vmServer":vmServer,"model":"instance","vmStorage":vmStorage,"vmInstance":vmInsList},
                                  context_instance=RequestContext(request))

@login_required
@permission_required('VManagePlatform.add_vmserver',login_url='/noperm/')
def addVmServer(request):
    if request.method == "GET":
        return render_to_response('vmServer/add_server.html',
                                  {"user":request.user,"localtion":[{"name":"Home","url":'/'},{"name":"Virtual Machine Manager","url":'#'},{"name":"Add host","url":"/addServer"}]},
                                  context_instance=RequestContext(request))

    elif  request.method == "POST":

        hostname=request.POST.get('hostname')
        username=request.POST.get('username',None)
        vm_type=request.POST.get('vm_type')
        server_ip=request.POST.get('server_ip')
        passwd=request.POST.get('passwd',None)

        try:
            VMS = LibvirtManage(server_ip,username,passwd,int(vm_type))
            SERVER = VMS.genre(model='server')
            VMS.close()

            try:
                VmServer.objects.create(hostname=hostname,
                                        username=username,
                                        vm_type=vm_type,
                                        server_ip=server_ip,
                                        passwd=passwd,
                                        status=0,)
                msg = "{} Added Successfully ".format(hostname)
                return render_to_response('vmServer/add_server.html',
                        {"user":request.user,"localtion":[{"name":"Home","url":'/'},{"name":"Virtual Machine Manager","url":'#'},{"name":"Add host","url":"/addServer"}],
                        "success_msg":msg},
                         context_instance=RequestContext(request))

            except Exception as e:
                return render_to_response('vmServer/add_server.html',
                                      {"user":request.user,"localtion":[{"name":"Home","url":'/'},{"name":"Virtual Machine Manager","url":'#'},{"name":"Add host","url":"/addServer"}],
                                       "errorInfo":e},
                                      context_instance=RequestContext(request))

        except Exception as e:
            return render_to_response('vmServer/add_server.html',
                                  {"user":request.user,"localtion":[{"name":"Home","url":'/'},{"name":"Virtual Machine Manager","url":'#'},{"name":"Add host","url":"/addServer"}],
                                   "errorInfo":e},
                                  context_instance=RequestContext(request))

@login_required(login_url='/login')
def allInstance(request):

    vmList = VmServer.objects.all().order_by("-id")
    mem_list = []
    inStanceList = []
    count=0
    count2=0

    # Checking host list is empty
    try:
        vmList[0].id
    except:
        return render_to_response('vmInstance/all_instance.html',{"localtion":[{"name":"Home","url":'/'},{"name":"Virtual machine instance","url":'#'},{"name":"List of virtual machine instances","url":"/0/"}],"SERV":"Host list is Empty"},context_instance=RequestContext(request))


    for vm in vmList:

        hostIsAlive = True
        hostIncludesVM = True

        try:
            vServer = VmServer.objects.get(id=str(vm.id))
        except:
            return render_to_response('404.html',context_instance=RequestContext(request))

        # Checking closed hosts.
        try:

            VMS = LibvirtManage(vServer.server_ip,vServer.username, vServer.passwd, vServer.vm_type)
            SERVER = VMS.genre(model='server')
            VMS.close()
            VmInfo = SERVER.getVmServerInfo()
            userList = User.objects.all()

            if not SERVER.getAllInstance():
                hostIncludesVM = False
        except:
            hostIsAlive = False
            pass

        if hostIsAlive:
            if hostIncludesVM: # Host is Alive and includes VM
                try:
                    #emre test
                    try:
                        VMS1 = LibvirtManage(vServer.server_ip,vServer.username, vServer.passwd, vServer.vm_type)
                        SERVER1 = VMS1.genre(model='server')
                        vmInstance = SERVER1.getVmInstanceInfo(server_ip=vServer.server_ip)
                        vmIns = vmInstance.get('active').get('number') + vmInstance.get('inactice').get('number')

                        for i in range(len(vmIns)):
                            data = dict()
                            data['host']=vServer.server_ip
                            print "for test"
                            data['name']=vmIns[i].get('name')
                            data['mem_per']=vmIns[i].get('mem_per')
                            mem_list.append(data)

                        VMS1.close()

                    except:
                        print "Memory listesi olurulamadi"

                    #emre test bitiş

                    inStanceList2 = SERVER.getVmInstanceBaseInfo(server_ip=vServer.server_ip,server_id=vServer.id)
                    inStanceList+=inStanceList2

                    for ll in inStanceList2:
                        if inStanceList[count]['server_ip']==vmList[count2].server_ip:
                            pass
                        else:
                            count2+=1

                        inStanceList[count]['hostname']=vmList[count2].hostname
                        inStanceList[count]['hserver_ip']=vmList[count2].server_ip
                        inStanceList[count]['cpu_total']=vmList[count2].cpu_total
                        inStanceList[count]['mem']=vmList[count2].mem
                        inStanceList[count]['instance']=vmList[count2].instance
                        inStanceList[count]['hstatus']=vmList[count2].status
                        inStanceList[count]['id']=vmList[count2].id
                        inStanceList[count]['hInfo']=VmInfo

                        try:
                            eth0_ip = str(inStanceList[count]['ip'][-1]['eth0']['addr'])
                        except:
                            eth0_ip = ""
                            pass

                        try:  # If VM exist in DB: UPDATE record; Else Create NEW record
                            existing_vm=VmServerInstance.objects.get(server_id=inStanceList[count]['id'], name=inStanceList[count]['name'])
                            existing_vm.status=inStanceList[count]['status']
                            existing_vm.cpu = inStanceList[count]['cpu']
                            existing_vm.mem = inStanceList[count]['memo']
                            existing_vm.token = str(inStanceList[count]['token'])
                            if inStanceList[count]['status']==1:existing_vm.ips=eth0_ip
                            existing_vm.save()
                            pass
                        except:
                            VmServerInstance.objects.create(
                                                            server_id=inStanceList[count]['id'],
                                                            name=str(inStanceList[count]['name']),
                                                            #ips=str(inStanceList[count]['server_ip']),
                                                            ips=eth0_ip,
                                                            cpu=inStanceList[count]['cpu'],
                                                            mem=inStanceList[count]['memo'],
                                                            status=inStanceList[count]['status'],
                                                            token=str(inStanceList[count]['token']),
                                                            owner=vServer.username
                                                       )
                            pass

                        count+=1
                except:
                    inStanceList = None
                    continue

            else: #Host is Alive but not include VM

                inStanceList+={'status': 0},
                inStanceList[count]['hostname']=vm.hostname
                inStanceList[count]['hserver_ip']=vm.server_ip
                inStanceList[count]['hstatus']=0
                inStanceList[count]['id']=vm.id
                inStanceList[count]['hInfo']=VmInfo
                count+=1
                try:
                    VmServerInstance.objects.filter(server_id=vm.id).delete()
                except:
                    continue


        else: # Host is not Alive
            try:
                unreachableVmList = VmServerInstance.objects.filter(server_id=vm.id)
                if len(unreachableVmList) > 0 :
                    hostIncludesVM = True
                else:
                    hostIncludesVM = False
            except:
                hostIncludesVM = False
                pass


            if hostIncludesVM: # Host is not Alive but includes VM
                for unrVm in unreachableVmList:

                    inStanceList+={'status': 7},
                    inStanceList[count]['hostname']=vm.hostname
                    inStanceList[count]['hserver_ip']=vm.server_ip
                    inStanceList[count]['hstatus']=1
                    inStanceList[count]['id']=vm.id
                    inStanceList[count]['server_ip']=vm.server_ip

                    inStanceList[count]['name'] = unrVm.name
                    inStanceList[count]['memo'] = unrVm.mem
                    inStanceList[count]['cpu'] = unrVm.cpu
                    inStanceList[count]['server_id'] = unrVm.server_id
                    inStanceList[count]['hInfo']={'status':"0",'cpu_total':"None",'mem':"None",'server_id':unrVm.server_id}
                    count+=1


            # Host is not Alive and not includes VM
            else:
                inStanceList+={'status': 0},
                inStanceList[count]['hostname']=vm.hostname
                inStanceList[count]['hserver_ip']=vm.server_ip
                inStanceList[count]['hstatus']=1
                inStanceList[count]['id']=vm.id
                inStanceList[count]['hInfo']={'cpu_total':"None",'mem':"None"}
                count+=1

    return render_to_response('vmInstance/all_instance.html',{"user":request.user,"localtion":[{"name":"Home","url":'/'},{"name":"List of virtual machine instances","url":'#'}],
                                            "inStanceList":inStanceList,"mem_list":mem_list,"vmServer":vServer,"userList":userList},
                              context_instance=RequestContext(request))
