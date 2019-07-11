#!/usr/bin/env python
# _#_ coding:utf-8 _*_
from django.http import JsonResponse
from django.shortcuts import render,redirect
import json
import random

from django.contrib.auth.decorators import login_required
from VManagePlatform.utils.vMConUtils import LibvirtManage
from VManagePlatform.models import VmServer,VmLogs
from VManagePlatform.tasks import revertSnapShot
from VManagePlatform.tasks import snapInstace
from VManagePlatform.tasks import recordLogs

@login_required
def handleSnapshot(request,id):
    try:
        vServer = VmServer.objects.get(id=id)
    except Exception,e:
        return JsonResponse({"code":500,"msg":"Host resource not found","data":e})
    if request.method == "POST":
        op = request.POST.get('op')
        insName = request.POST.get('vm_name')
        snapName = request.POST.get('snap_name')
        if op in ['view','resume','delete','add'] and request.user.has_perm('VManagePlatform.change_vmserverinstance'):
            try:
                VMS = LibvirtManage(vServer.server_ip,vServer.username, vServer.passwd, vServer.vm_type)
            except Exception,e:
                return  JsonResponse({"code":500,"msg":"The server connection failed. .","data":e})
            try:
                INSTANCE = VMS.genre(model='instance')
                instance = INSTANCE.queryInstance(name=str(insName))
                if op == 'view':
                    snap = INSTANCE.snapShotView(instance, snapName)
                    VMS.close()
                    if snap:return JsonResponse({"code":200,"data":snap.replace('<','&lt;').replace('>','&gt;'),"msg":"search successful."})
                    else:return JsonResponse({"code":500,"data":"Check no result","msg":"Check no result"})

                elif op == 'resume':
                    try:
                        revertSnapShot(request.POST,str(request.user))
                        VMS.close()
                    except:
                        pass
                    return JsonResponse({"code":200,"data":None,"msg":"The snapshot recovery task was submitted successfully."})

                elif op == 'add':

                    dupliate_snapName = INSTANCE.snapShotExists(instance, snapName)
                    if dupliate_snapName:
                        VMS.close()
                        code="500"
                        result="FAILED"
                        return JsonResponse({"code":code,"data":None,"msg":" %s: Snapshot Name Already Exists" % (result)})
                    else:
                        snap = INSTANCE.snapShotCreate(instance, snapName)
                        VMS.close()
                        if snap:
                            code="200"
                            result="SUCCESSFUL"
                        else:
                            code="500"
                            result="FAILED"
                        try:
                            recordLogs(server_id=vServer.id,vm_name=request.POST.get('vm_name'),
                                         content="Add virtual machine {name} Snapshot {snapName}".format(name=request.POST.get('vm_name'),
                                         snapName=snapName), user=str(request.user),status=0, result=result)
                        except:
                            pass

                        return JsonResponse({"code":code,"data":None,"msg":"Snapshot create %s" % (result)})

                elif op == 'delete':
                    snap = INSTANCE.snapShotDelete(instance, snapName)
                    VMS.close()
                    if isinstance(snap, int):
                        code="200"
                        result="SUCCESSFUL"
                    else:
                        code="500"
                        result="FAILED"
                    try:
                        recordLogs(server_id=vServer.id,vm_name=request.POST.get('vm_name'),
                                     content="Delete virtual machine {name} Snapshot {snapName}".format(name=request.POST.get('vm_name'),
                                     snapName=snapName), user=str(request.user),status=0, result=result)
                    except:
                        pass
                    return JsonResponse({"code":code,"data":None,"msg":"Snapshot delete %s" % (result)})
                               
            except Exception,e:
                return JsonResponse({"code":500,"msg":"The virtual machine snapshot operation failed. .","data":e})
        else:
            return JsonResponse({"code":500,"msg":"Unsupported operation.","data":e})
