#!/usr/bin/env python  
# _#_ coding:utf-8 _*_ 
from django.http import JsonResponse
from django.shortcuts import render_to_response
from djcelery.models  import PeriodicTask,CrontabSchedule,WorkerState,TaskState,IntervalSchedule
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from celery.registry import tasks
from celery.five import keys, items
from django.contrib.auth.decorators import permission_required

@login_required
@permission_required('djcelery.change_periodictask',login_url='/noperm/')
def configTask(request):
    if request.method == "GET":
        #Get registered tasks
        regTaskList = []
        for task in  list(keys(tasks)):
            if task.startswith('VManagePlatform'):regTaskList.append(task)
        try:
            crontabList = CrontabSchedule.objects.all().order_by("-id")
            intervalList = IntervalSchedule.objects.all().order_by("-id")
            taskList = PeriodicTask.objects.all().order_by("-id")
        except:
            crontabList = []
            intervalList = []
            taskList = []
        return render_to_response('vmTasks/config_task.html',
                                  {"user":request.user,"localtion":[{"name":"Home","url":'/'},{"name":"Task scheduling","url":'#'},
                                                                    {"name":"Configuration Center","url":"/configTask"}],
                                    "crontabList":crontabList,"intervalList":intervalList,"taskList":taskList,
                                    "regTaskList":regTaskList},
                                  context_instance=RequestContext(request))
    elif request.method == "POST":
        op = request.POST.get('op') 
        if op in ['addCrontab','delCrontab','addInterval',
                  'delInterval','addTask','editTask',
                  'delTask'] and request.user.has_perm('djcelery.change_periodictask'):
            if op == 'addCrontab':
                try:
                    CrontabSchedule.objects.create(minute=request.POST.get('minute'),hour=request.POST.get('hour'),
                                                      day_of_week=request.POST.get('day_of_week'),
                                                      day_of_month=request.POST.get('day_of_month'),
                                                      month_of_year=request.POST.get('month_of_year'),
                                                      )
                    return  JsonResponse({"code":200,"data":None,"msg":"Added successfully"})
                except:
                    return  JsonResponse({"code":500,"data":None,"msg":"add failed"})
            elif op == 'delCrontab':
                try:
                    CrontabSchedule.objects.get(id=request.POST.get('id')).delete()
                    return  JsonResponse({"code":200,"data":None,"msg":"successfully deleted"})
                except:
                    return  JsonResponse({"code":500,"data":None,"msg":"failed to delete"})  
            elif op == 'addInterval':
                try:
                    IntervalSchedule.objects.create(every=request.POST.get('every'),period=request.POST.get('period'))
                    return  JsonResponse({"code":200,"data":None,"msg":"Added successfully"})
                except:
                    return  JsonResponse({"code":500,"data":None,"msg":"add failed"})    
            elif op == 'delInterval':
                try:
                    IntervalSchedule.objects.get(id=request.POST.get('id')).delete()
                    return  JsonResponse({"code":200,"data":None,"msg":"successfully deleted"})
                except:
                    return  JsonResponse({"code":500,"data":None,"msg":"failed to delete"})
            elif op == 'addTask':
                try:
                    PeriodicTask.objects.create(name=request.POST.get('name'),
                                                interval_id=request.POST.get('interval',None),
                                                task=request.POST.get('task',None),
                                                crontab_id=request.POST.get('crontab',None),
                                                args = request.POST.get('args','[]'),
                                                kwargs = request.POST.get('kwargs','{}'),
                                                queue = request.POST.get('queue',None),
                                                enabled = int(request.POST.get('enabled',1)),
                                                expires = request.POST.get('expires',None)
                                                      )
                    return  JsonResponse({"code":200,"data":None,"msg":"Added successfully"})
                except Exception,e:
                    return  JsonResponse({"code":500,"data":str(e),"msg":"add failed"})    
            elif op == 'delTask':
                try:
                    PeriodicTask.objects.get(id=request.POST.get('id')).delete()
                    return  JsonResponse({"code":200,"data":None,"msg":"successfully deleted"})
                except:
                    return  JsonResponse({"code":500,"data":None,"msg":"failed to delete"})
            elif op == 'editTask':
                try:
                    task = PeriodicTask.objects.get(id=request.POST.get('id'))
                    task.name = request.POST.get('name')
                    task.interval_id = request.POST.get('interval',None)
                    task.crontab_id = request.POST.get('crontab',None)
                    task.args = request.POST.get('args')
                    task.kwargs = request.POST.get('kwargs')
                    task.queue = request.POST.get('queue',None)
                    task.expires = request.POST.get('expires',None)
                    task.enabled = int(request.POST.get('enabled'))
                    task.save()
                    return  JsonResponse({"code":200,"data":None,"msg":"Successfully modified"})
                except Exception,e:
                    return  JsonResponse({"code":500,"data":str(e),"msg":"fail to edit"})
                             
        else:return  JsonResponse({"code":500,"data":None,"msg":"Unsupported operation or you do not have permission to operate this item."})            
    else:return  JsonResponse({"code":500,"data":None,"msg":"Unsupported HTTP operations"})   
    
    
    
@login_required
@permission_required('djcelery.read_periodictask',login_url='/noperm/')
def viewTask(request):
    if request.method == "GET":
        try:
            task = {}
            taskList = PeriodicTask.objects.all().order_by("-id")
            for ds in PeriodicTask.objects.all():
                task[ds.task] = [ds.name]
            taskLog = []
            if request.GET.get('taskid'):
                tasks =  PeriodicTask.objects.get(id=int(request.GET.get('taskid')))
                dataList = TaskState.objects.filter(name=tasks.task).order_by("-id")[0:300]
            else:
                dataList = TaskState.objects.all().order_by("-id")[0:300]
            for ds in dataList:
                if task.has_key(ds.name):ds.name = task[ds.name][0]
                ds.args = ds.args.replace('[u','[')
                taskLog.append(ds)
        except:
            taskLog = []
        return render_to_response('vmTasks/view_task.html',
                                  {"user":request.user,"localtion":[{"name":"Home","url":'/'},{"name":"Task scheduling","url":'#'},
                                                                    {"name":"Run log","url":"/viewTask"}],
                                    "taskLog":taskLog,"taskList":taskList},
                                  context_instance=RequestContext(request))
    elif request.method == "POST":
        op = request.POST.get('op')
        if op in ['view','delete'] and request.user.has_perm('djcelery.change_taskstate'):
            try:
                task = {}
                for ds in PeriodicTask.objects.all():
                    task[ds.task] = ds.name
                taskLog = TaskState.objects.get(id=request.POST.get('id'))
            except:
                return JsonResponse({"code":500,"data":None,"msg":"Task does not exist"})
            if op == 'view':
                try:
                    data = dict()
                    work = WorkerState.objects.get(id=taskLog.worker_id)
                    data['id'] = taskLog.id
                    data['task_id'] = taskLog.task_id
                    data['worker'] = work.hostname
                    if task.has_key(taskLog.name):data['name'] = task[taskLog.name]
                    else:data['name'] = taskLog.name
                    data['tstamp'] = taskLog.tstamp
                    data['args'] = taskLog.args.replace('[u','[')
                    data['kwargs'] = taskLog.kwargs
                    data['result'] = taskLog.result
                    data['state'] = taskLog.state
                    data['runtime'] = taskLog.runtime
                    return  JsonResponse({"code":200,"data":data,"msg":"Successful operation"})
                except Exception,e:
                    return  JsonResponse({"code":500,"data":None,"msg":"Log view failed."})
            elif op == 'delete':
                try:
                    taskLog.delete()
                    return  JsonResponse({"code":200,"data":None,"msg":"successfully deleted"})
                except:
                    return  JsonResponse({"code":500,"data":None,"msg":"Log deletion failed"})
        else:return  JsonResponse({"code":500,"data":None,"msg":"Unsupported operation or you do not have permission to operate this item."})            
    else:return  JsonResponse({"code":500,"data":None,"msg":"Unsupported HTTP operations"})