#!/usr/bin/env python
# _#_ coding:utf-8 _*_

from django.conf import settings
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response,render
from django.contrib import auth
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from VManagePlatform.models import VmServer,VmServerInstance
from VManagePlatform.utils.vConnUtils import TokenUntils
from VManagePlatform.models import VmLogs

import time
from VManagePlatform.utils.vMConUtils import LibvirtManage
from VManagePlatform.const import Const
from VManagePlatform.utils.vConnUtils import CommTools
from VManagePlatform.tasks import migrateInstace,cloneInstace,recordLogs
from VManagePlatform.utils.vBrConfigUtils import BRManage
from django.contrib.auth.models import User

@login_required(login_url='/login')
def index(request):
    vmRun = 0
    vmStop = 0
    vmTotal = 0
    serRun = 0
    serStop = 0
    logList = None
    vmList = []
    serList= []

    try:
        serList=VmServer.objects.all().order_by("-id")
        for ser in serList:

            '''
                1 - HOST ERISILEBILIRLIK KONTROLU
            '''
            try:
                hostCon = LibvirtManage(ser.server_ip,ser.username, ser.passwd, ser.vm_type)
                host = hostCon.genre(model='server')
                hostCon.close()
                serRun = serRun + 1
            except:
                serStop = serStop + 1

            '''
                2 - INSTANCE ERISILEBILIRLIK KONTROLU
            '''
            try:
                vmList = host.getVmInstanceBaseInfo(server_ip=ser.server_ip,server_id=ser.id)
                vmTotal += len(vmList)
                for vm in vmList:
                    try:
                        if vm['status'] == 1:
                            vmRun = vmRun +1
                        else:
                            vmStop = vmStop +1
                    except:
                        pass

            except:
                vmList = []

    except:
        serList = []

    totalInfo = {"vmRun":vmRun,"vmStop":vmStop,"serTotal":len(serList),
                 "serStop":serStop,"vmTotal":vmTotal,"serRun":serRun}
    return render_to_response('index.html',{"user":request.user,"localtion":[{"name":"Home","url":'/'}],
                                            "logList":logList,"totalInfo":totalInfo,"msgTotal":serStop+vmStop},
                              context_instance=RequestContext(request))
                              
def login(request):
    if request.session.get('username') is not None:
        return HttpResponseRedirect('/profile',{"user":request.user})
    else:
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = auth.authenticate(username=username,password=password)
        if user and user.is_active:
            auth.login(request,user)
            request.session['username'] = username
            return HttpResponseRedirect('/profile',{"user":request.user})
        else:
            if request.method == "POST":
                return render_to_response('login.html',{"login_error_info":"The username is good, or the password is wrong!"},
                                                        context_instance=RequestContext(request))
            else:
                return render_to_response('login.html',context_instance=RequestContext(request))

@login_required
def permission(request,args=None):
    return render_to_response('noperm.html',{"user":request.user},
                                  context_instance=RequestContext(request))

@login_required
def run_vnc(request,id,vnc,uuid):
    '''
        Call the VNC proxy for remote control
    '''
    vServer = VmServer.objects.get(id=id)
    tokenStr = uuid + ': ' + vServer.server_ip + ':' + str(vnc)
    TokenUntils.writeVncToken(filename=uuid,token=tokenStr)
    return render(request, 'vnc/vnc_auto.html',{"vnc_port":settings.VNC_PROXY_PORT,
                                                    "vnc_token":uuid,
                                                    })

def logout(request):
    auth.logout(request)
    return HttpResponseRedirect('/login')
