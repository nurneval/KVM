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
import spur

@login_required
def handleBackup(request,id):
    try:
        vServer = VmServer.objects.get(id=id)
    except Exception,e:
        return JsonResponse({"code":500,"msg":"Host resource not found","data":e})
    if request.method == "POST":
        op = request.POST.get('op')
        insName = request.POST.get('vm_name')
        backupName = request.POST.get('backup_name')
        if op in ['view','resume','delete','add'] and request.user.has_perm('VManagePlatform.change_vmserverinstance'):
            try:
                VMS = LibvirtManage(vServer.server_ip,vServer.username, vServer.passwd, vServer.vm_type)
            except Exception,e:
                return  JsonResponse({"code":500,"msg":"The server connection failed. .","data":e})
            try:
                INSTANCE = VMS.genre(model='instance')
                instance = INSTANCE.queryInstance(name=str(insName))
                if op == 'view':
                    backup = INSTANCE.backupView(instance, backupName)
                    VMS.close()
                    if backup:return JsonResponse({"code":200,"data":backup.replace('<','&lt;').replace('>','&gt;'),"msg":"search successful."})
                    else:return JsonResponse({"code":500,"data":"Check no result","msg":"Check no result"})
                elif op == 'resume':
                    revertBackup.delay(request.POST,str(request.user))
                    VMS.close()
                    return JsonResponse({"code":200,"data":None,"msg":"The backup recovery task was submitted successfully."})

                elif op == 'add':
                    dupliateBackupName = INSTANCE.backupExists(instance, backupName)
                    if dupliateBackupName:
                        VMS.close()
                        code="500"
                        result="FAILED"
                        return JsonResponse({"code":code,"data":None,"msg":" %s: Backup Name Already Exists" % (result)})
                    else:
                        backup = INSTANCE.backupCreate(instance, backupName)
                        VMS.close()
                        if backup:
                            code="200"
                            result="SUCCESSFUL"
                        else:
                            code="500"
                            result="FAILED"
                        try:
                            recordLogs(server_id=vServer.id,vm_name=request.POST.get('vm_name'),
                                         content="Add virtual machine {name} Backup {backupName}".format(name=request.POST.get('vm_name'),
                                         backupName=backupName), user=str(request.user),status=0, result=result)
                        except:
                            pass

                        return JsonResponse({"code":code,"data":None,"msg":"Backup create %s" % (result)})

                elif op == 'delete':
                    backup = INSTANCE.backupDelete(instance, backupName)
                    VMS.close()
                    if isinstance(backup, int):
                        code="200"
                        result="SUCCESSFUL"
                    else:
                        code="500"
                        result="FAILED"
                    try:
                        recordLogs(server_id=vServer.id,vm_name=request.POST.get('vm_name'),
                                     content="Delete virtual machine {name} Backup {backupName}".format(name=request.POST.get('vm_name'),
                                     backupName=backupName), user=str(request.user),status=0, result=result)
                    except:
                        pass
                    return JsonResponse({"code":code,"data":None,"msg":"Backup delete %s" % (result)})

            except Exception,e:
                return JsonResponse({"code":500,"msg":"The virtual machine backup operation failed. .","data":e})
        elif op == 'AAA' and request.user.has_perm('VManagePlatform.change_vmserverinstance'):
            return JsonResponse({"code":200,"data":None,"msg":" AAA "})
        else:
            return JsonResponse({"code":500,"msg":"Unsupported operation.","data":e})

class backupManager(object):

    def __init__(self, id, hostname, username, passwd):

        self.hostname = hostname
        self.username = username
        self.passwd = passwd
        self.id = id
        self.result = "A_3"


    def listVmBackup(self, vmName):
        try:
            vServer = VmServer.objects.get(id=self.id)
            __backup_dir = "/var/lib/libvirt/backup/VMARSIV/VMANAGE_BACKUPS/%s" % vmName
            try:
                shell = spur.SshShell(hostname=self.hostname, username="root", password=self.passwd)
                with shell:
                    self.result = shell.run(["ls", __backup_dir])
                pass
            except:
                self.result = "A_1"
                pass
            return self.result.output.split()
        except Exception,e:
            self.result = "A_2"
            return self.result
