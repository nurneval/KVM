#!/usr/bin/env python  
# _#_ coding:utf-8 _*_ 
from django.http import JsonResponse
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from VManagePlatform.models import VmLogs,VmServerInstance,VmServer
from django.contrib.auth.models import User

@login_required
def profile(request):
    if request.method == "GET":
        try:
            if request.user.is_superuser:
                vmList = VmServerInstance.objects.select_related().all().order_by("-id")
            else:
                vmList = VmServerInstance.objects.select_related().filter(owner=request.user).all().order_by("-id")[0:200]
            logList = VmLogs.objects.filter(user=request.user).all().order_by("-create_time")
        except:
            logList = None
            vmList = None
        return render_to_response('profile.html',
                                  {"user":request.user,"localtion":[{"name":"Home","url":'/'},{"name":"UserConfiguration","url":'/profile'}],
                                   "logList":logList,"vmList":vmList
                                   },context_instance=RequestContext(request))
    elif request.method == "POST":
        op = request.POST.get('op')
        if op in ['assign','password','viewlog']:
            if op == 'assign':
                try:
                    server = VmServer.objects.get(id=int(request.POST.get('server')))
                    instance = VmServerInstance.objects.get(server_id=server,name=request.POST.get('name'))
                    instance.owner = request.POST.get('username')
                    instance.save()
                    return JsonResponse({"code":200,"data":None,"msg":"The virtual machine is assigned successfully."})
                except Exception,e:
                    return JsonResponse({"code":500,"data":e,"msg":"Failed to allocate virtual machines."})
            elif op == 'password':
                if request.POST.get('n_pwd') == request.POST.get('c_pwd'):
                    try:
                        user = User.objects.get(username=request.POST.get('username'))
                        user.set_password(request.POST.get('c_pwd'))
                        user.save()
                        return JsonResponse({'msg':"Password reset complete.","code":200,'data':None})
                    except Exception,e:
                        return JsonResponse({'msg':'failed',"code":500,'data':"The system is busy please try later."}) 
                else:
                    return JsonResponse({'msg':'The new password is inconsistent and the password change failed.',"code":500,'data':None})
            elif op == 'viewlog':
                try:
                    count = int(request.POST.get('count')) - 10
                    logList = VmLogs.objects.filter(user=request.user).all().order_by("-create_time")
                    dataList = []
                    for ds in logList:
                        data  = dict()
                        data['id'] = ds.id
                        data['content'] = ds.content
                        data['user'] = ds.user
                        data['vm_name'] = ds.vm_name
                        data['status'] = ds.status
                        data['create_time'] = ds.create_time
                        data['result'] = ds.result
                        dataList.append(data)
                    if len(dataList) > 0:return JsonResponse({'msg':"The data was loaded successfully.","code":200,'data':dataList})
                    else:return JsonResponse({'msg':'No more news',"code":500,'data':None})
                except Exception,e:
                    return JsonResponse({'msg':str(e),"code":500,'data':None})             
        else:return JsonResponse({"code":500,"data":None,"msg":"Unsupported operation."})

def delete_logs(request):
    try:
        vmLogs = VmLogs.objects.all();
    except:
        return render_to_response('404.html',context_instance=RequestContext(request))

    if request.method == "POST":
        try:
            id_list = request.POST.getlist('selected_ids[]')
            for id in id_list:
                vmLogs.filter(id=id).update(isRead="1")
            return JsonResponse({'msg':"Selected logs deleted successfully.","code":200})

        except Exception as e:
            return JsonResponse({"code":500,"data":None,"msg":e})

