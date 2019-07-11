#!/usr/bin/env python
# _#_ coding:utf-8 _*_
from django.http import JsonResponse
from VManagePlatform.models import VmServer
from django.contrib.auth.decorators import login_required
from VManagePlatform.utils.vMConUtils import LibvirtManage

@login_required
def handleVolume(request):
    if request.method == "POST":
        op = request.POST.get('op')
        server_id = request.POST.get('server_id')
        pool_name = request.POST.get('pool_name')
        if op in ['delete','add'] and request.user.has_perm('VManagePlatform.change_vmserverinstance'):
            try:
                vServer = VmServer.objects.get(id=server_id)
            except:
                return JsonResponse({"code":500,"data":None,"msg":"The host does not exist."})
            VMS = LibvirtManage(vServer.server_ip,vServer.username, vServer.passwd, vServer.vm_type)
            STORAGE = VMS.genre(model='storage')
            if STORAGE:
                pool = STORAGE.getStoragePool(pool_name=pool_name)
                if pool:
                    volume = STORAGE.getStorageVolume(pool=pool, volume_name=request.POST.get('vol_name'))
                    if op == 'add':
                        if volume:return JsonResponse({"code":500,"data":None,"msg":"Volume already exists"})
                        else:
                            status = STORAGE.createVolumes(pool=pool, volume_name=request.POST.get('vol_name'),
                                                volume_capacity=int(request.POST.get('vol_size')),drive=request.POST.get('vol_drive'))
                            VMS.close()
                            if isinstance(status,str) :return  JsonResponse({"code":500,"data":None,"msg":status})
                            else:return  JsonResponse({"code":200,"data":None,"msg":"The volume was created successfully."})
                    elif op == 'delete':
                        if volume:
                            status = STORAGE.deleteVolume(pool=pool, volume_name=request.POST.get('vol_name'))
                            VMS.close()
                            if isinstance(status, str):return  JsonResponse({"code":500,"data":status,"msg":"Failed to delete the volume."})
                            else:return  JsonResponse({"code":200,"data":None,"msg":"Deleted the volume successfully."})
                        else:return  JsonResponse({"code":500,"data":None,"msg":"The deletion of the volume failed and the volume does not exist."})
                else:return  JsonResponse({"code":500,"data":None,"msg":"Storage pool does not exist."})
            else:
                return  JsonResponse({"code":500,"data":None,"msg":"Host connection failed."})
        else:
            return  JsonResponse({"code":500,"data":None,"msg":"Does not support operation."})
    else:
        return  JsonResponse({"code":500,"data":None,"msg":"Unsupported HTTP operation."})
