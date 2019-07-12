#!/usr/bin/env python  
# _#_ coding:utf-8 _*_ 
from django.http import JsonResponse
from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required
from VManagePlatform.utils.vMConUtils import LibvirtManage
from django.template import RequestContext
from VManagePlatform.models import VmServer
from VManagePlatform.const.Const import CreateBridgeNetwork,CreateNatNetwork
from VManagePlatform.utils.vBrConfigUtils import BRManage
from VManagePlatform.tasks import recordLogs

@login_required
def configNetwork(request,id):
    try:
        vServer = VmServer.objects.get(id=id)
    except Exception,e:
        return render_to_response('404.html',context_instance=RequestContext(request))
    if request.method == "GET":
        try:
            VMS = LibvirtManage(vServer.server_ip,vServer.username, vServer.passwd, vServer.vm_type)
            NETWORK = VMS.genre(model='network')
            if NETWORK:
                netList = NETWORK.listNetwork()
                insList = NETWORK.listInterface()
            else:return render_to_response('404.html',context_instance=RequestContext(request))
        except Exception,e:
            netList = None
        return render_to_response('vmNetwork/add_network.html',
                                  {"user":request.user,"localtion":[{"name":"Home","url":'/'},{"name":"Network management","url":'/addNetwork'}],
                                   "vmServer":vServer,"netList":netList,"insList":insList},context_instance=RequestContext(request))    
    elif request.method == "POST" and request.user.has_perm('VManagePlatform.change_vmserverinstance'):
        try:
            VMS = LibvirtManage(vServer.server_ip,vServer.username, vServer.passwd, vServer.vm_type)
            NETWORK = VMS.genre(model='network')
            if request.POST.get('network-mode') == 'bridge':
                SSH = BRManage(hostname=vServer.server_ip,port=22)
                OVS = SSH.genre(model='ovs')
                BRCTL = SSH.genre(model='brctl')
                if NETWORK and OVS:
                    status = NETWORK.getNetwork(netk_name=request.POST.get('bridge-name'))
                    if status:
                        VMS.close() 
                        return  JsonResponse({"code":500,"msg":"The network already exists.","data":None}) 
                    else:
                        if request.POST.get('mode') == 'openvswitch':
                            status =  OVS.ovsAddBr(brName=request.POST.get('bridge-name'))#Create a bridge using ovs
                            if status.get('status') == 'success':
                                status = OVS.ovsAddInterface(brName=request.POST.get('bridge-name'), interface=request.POST.get('interface'))#Create a bridge with ovs and bind the port
                            if status.get('status') == 'success':
                                if request.POST.get('stp') == 'on':status = OVS.ovsConfStp(brName=request.POST.get('bridge-name'))#Whether to enable stp
                        elif request.POST.get('mode') == 'brctl':
                            if request.POST.get('stp') == 'on':status = BRCTL.brctlAddBr(iface=request.POST.get('interface'),brName=request.POST.get('bridge-name'),stp='on')
                            else:status = BRCTL.brctlAddBr(iface=request.POST.get('interface'),brName=request.POST.get('bridge-name'),stp=None)
                        SSH.close()
                        if  status.get('status') == 'success':                          
                            XML = CreateBridgeNetwork(name=request.POST.get('bridge-name'),
                                                bridgeName=request.POST.get('bridge-name'),
                                                mode=request.POST.get('mode'))
                            result = NETWORK.createNetwork(XML)
                            VMS.close()
                        else:
                            VMS.close()
                            return  JsonResponse({"code":500,"msg":status.get('stderr'),"data":None}) 
                        if isinstance(result,int): return  JsonResponse({"code":200,"msg":"The network was created successfully.","data":None})   
                        else:return  JsonResponse({"code":500,"msg":result,"data":None})   
                else:return  JsonResponse({"code":500,"msg":"Network creation failed.","data":None})
            elif request.POST.get('network-mode') == 'nat':
                XML = CreateNatNetwork(netName=request.POST.get('nat-name'),dhcpIp=request.POST.get('dhcpIp'),
                                       dhcpMask=request.POST.get('dhcpMask'),dhcpStart=request.POST.get('dhcpStart'),
                                       dhcpEnd=request.POST.get('dhcpEnd'))
                result = NETWORK.createNetwork(XML)   
                if isinstance(result,int):return  JsonResponse({"code":200,"msg":"The network was created successfully.","data":None})   
                else:return  JsonResponse({"code":500,"msg":result,"data":None})                                                                            
        except Exception,e:
            return  JsonResponse({"code":500,"msg":"The server connection failed. .","data":e})  
    else:return  JsonResponse({"code":500,"data":None,"msg":"Unsupported HTTP operation or you do not have permission to operate this item"}) 
    
            
@login_required
def handleNetwork(request,id):
    try:
        vServer = VmServer.objects.get(id=id)
    except Exception,e:
        return JsonResponse({"code":500,"msg":"Host resource not found","data":e})
    if request.method == "POST":
        op = request.POST.get('op')
        netkName = request.POST.get('netkName')
        if op in ['delete'] and request.user.has_perm('VManagePlatform.change_vmserverinstance'):
            try:
                VMS = LibvirtManage(vServer.server_ip,vServer.username, vServer.passwd, vServer.vm_type)       
            except Exception,e:
                return  JsonResponse({"code":500,"msg":"The server connection failed. .","data":e})             
            try:
                NETWORK = VMS.genre(model='network')
                netk = NETWORK.getNetwork(netk_name=netkName)
                mode = NETWORK.getNetworkType(netk_name=netkName).get('mode')
                if op == 'delete':
                    try:
                        SSH = BRManage(hostname=vServer.server_ip,port=22)
                        if mode == 'openvswitch':
                            OVS = SSH.genre(model='ovs') 
                            OVS.ovsDelBr(brName=netkName)
                        elif mode == 'brctl':
                            BRCTL = SSH.genre(model='brctl') 
                            BRCTL.brctlDownBr(brName=netkName)
                        SSH.close()
                    except:
                        pass
                    status = NETWORK.deleteNetwork(netk)
                    VMS.close() 
                    if status == 0:return JsonResponse({"code":200,"data":None,"msg":"Network deletion successful"})  
                    else:return JsonResponse({"code":500,"data":None,"msg":"Network deletion failed"})     
            except Exception,e:
                return JsonResponse({"code":500,"msg":"Failed to get network.","data":e}) 
        else:
            return JsonResponse({"code":500,"msg":"Unsupported operation.","data":e})                                 