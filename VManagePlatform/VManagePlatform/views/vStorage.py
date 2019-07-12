#!/usr/bin/env python  
# _#_ coding:utf-8 _*_ 
from django.http import JsonResponse
from django.shortcuts import render_to_response
from VManagePlatform.utils.vMConUtils import LibvirtManage
from VManagePlatform.models import VmServer
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from VManagePlatform.const.Const import StorageTypeXMLConfig



@login_required
def addStorage(request,id):
    try:
        vServer = VmServer.objects.get(id=id)
    except Exception,e:
        return JsonResponse({"code":500,"msg":"Host resource not found","data":e})
    if request.method == "POST" and request.user.has_perm('VManagePlatform.add_vmserverinstance'):
        pool_xml = StorageTypeXMLConfig(pool_type=request.POST.get('pool_type'),pool_name=request.POST.get('pool_name'),
                                        pool_spath=request.POST.get('pool_spath'),pool_tpath=request.POST.get('pool_tpath'),
                                        pool_host=request.POST.get('pool_host'))
        if pool_xml:           
            try:
                VMS = LibvirtManage(vServer.server_ip,vServer.username, vServer.passwd, vServer.vm_type)
                STORAGE = VMS.genre(model='storage')
                pool = STORAGE.getStoragePool(pool_name=request.POST.get('pool_name'))
                if pool is False:
                    storage = STORAGE.createStoragePool(pool_xml)
                    VMS.close()
                    if isinstance(storage,int):return JsonResponse({"code":200,"msg":"Storage pool added successfully","data":None})  
                    else:return  JsonResponse({"code":500,"msg":"Failed to create the storage pool.","data":None}) 
                else:
                    VMS.close()
                    return  JsonResponse({"code":400,"msg":"Storage pool already exists.","data":None})
            except Exception,e:
                return JsonResponse({"code":500,"msg":"Find host resources","data":e})
        else:
            return JsonResponse({"code":500,"msg":"Unsupported storage type or you do not have permission to operate this item","data":None})
        
@login_required
def listStorage(request,id):        
    if request.method == "GET":
        try:
            vServer = VmServer.objects.get(id=id)
        except Exception,e:
            return render_to_response('404.html',context_instance=RequestContext(request))
        try:
            VMS = LibvirtManage(vServer.server_ip,vServer.username, vServer.passwd, vServer.vm_type)
            SERVER = VMS.genre(model='server')
            if SERVER:
                storageList = SERVER.getVmStorageInfo()
                VMS.close()
            else:return render_to_response('404.html',context_instance=RequestContext(request))
        except Exception,e:
            return render_to_response('404.html',context_instance=RequestContext(request))        
        return render_to_response('vmStorage/list_storage.html',
                                  {"user":request.user,"localtion":[{"name":"Home","url":'/'},{"name":"Virtual machine instance","url":'#'},
                                                                    {"name":"Storage pool management","url":"/listStorage/%d/" % vServer.id}],
                                    "vmServer":vServer,"storageList":storageList}, context_instance=RequestContext(request))

@login_required
def viewStorage(request,id,name): 
    if request.method == "GET":
        try:
            vServer = VmServer.objects.get(id=id)
        except:
            return render_to_response('404.html',context_instance=RequestContext(request))        
        try:
            VMS = LibvirtManage(vServer.server_ip,vServer.username, vServer.passwd, vServer.vm_type)
            STORAGE = VMS.genre(model='storage')
            if STORAGE:
                storage = STORAGE.getStorageInfo(name)
                VMS.close()
            else:return render_to_response('404.html',context_instance=RequestContext(request))
        except Exception,e:
            return render_to_response('404.html',context_instance=RequestContext(request))    
        return render_to_response('vmStorage/view_storage.html',
                                  {"user":request.user,"localtion":[{"name":"Home","url":'/'},{"name":"Virtual machine instance","url":'#'},
                                                                    {"name":"Storage pool management","url":"/listStorage/%d/" % vServer.id},
                                                                    {"name":"Storage pool details","url":"/viewStorage/%d/%s/" % (vServer.id,name)}],
                                    "vmServer":vServer,"storage":storage}, context_instance=RequestContext(request))
        
@login_required
def handleStorage(request,id):
    if request.method == "POST":
        try:
            vServer = VmServer.objects.get(id=id)
        except Exception,e:
            return JsonResponse({"code":500,"msg":"Host resource not found","data":e})      
        op = request.POST.get('op') 
        pool_name = request.POST.get('pool_name') 
        if op in ['delete','disable','refresh'] and request.user.has_perm('VManagePlatform.change_vmserverinstance'):
            VMS = LibvirtManage(vServer.server_ip,vServer.username, vServer.passwd, vServer.vm_type)
            STORAGE = VMS.genre(model='storage')
            pool = STORAGE.getStoragePool(pool_name=pool_name)  
            if pool:
                if op == 'delete':                                   
                    result = STORAGE.deleteStoragePool(pool=pool)
                elif op == 'refresh': 
                    result = STORAGE.refreshStoragePool(pool=pool)
                VMS.close()
                if isinstance(result,int):return  JsonResponse({"code":200,"msg":"Successful operation。","data":None})
                else:return  JsonResponse({"code":500,"msg":result})                    
            else:return JsonResponse({"code":500,"msg":"Storage pool does not exist.","data":e}) 
        else:return  JsonResponse({"code":500,"data":None,"msg":"No action is supported or you do not have permission to operate this item"})                        
    else:return  JsonResponse({"code":500,"data":None,"msg":"Unsupported HTTP operations"})                