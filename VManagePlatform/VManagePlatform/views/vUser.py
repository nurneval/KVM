#!/usr/bin/env python
# _#_ coding:utf-8 _*_
from django.contrib.auth.models import User,Permission,Group
from django.http import JsonResponse
from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.contrib.auth.decorators import permission_required


def register(request):
    if request.method == "POST":
        if request.POST.get('password') == request.POST.get('c_password'):
            try:
                user = User.objects.filter(username=request.POST.get('username'))
                if len(user)>0:return JsonResponse({"code":500,"data":None,"msg":"Registration failed and the user already exists."})
                else:
                    user = User()
                    user.username = request.POST.get('username')
                    user.email = request.POST.get('email')
                    user.is_staff = 0
                    user.is_active = 0
                    user.is_superuser = 0
                    user.set_password(request.POST.get('password'))
                    user.save()
                    return JsonResponse({"code":200,"data":None,"msg":"User registration is successful"})
            except Exception,e:
                return JsonResponse({"code":500,"data":None,"msg":"User registration failed"})
        else:return JsonResponse({"code":500,"data":None,"msg":"Inconsistent password, user registration failed."})

@login_required
@permission_required('auth.change_user',login_url='/noperm/')
def usermanage(request,id):
    if request.method == "GET":
        userPermList = []
        userGroupList = []
        try:
            user = User.objects.get(id=id)
            #Get user permission list
            for perm in user.user_permissions.values():
                userPermList.append(perm.get('id'))
            #Get user group list
            for group in user.groups.values():
                userGroupList.append(group.get('id'))
            permList = Permission.objects.all()
            groupList = Group.objects.all()
        except Exception,e:
            user = None
            permList = []
            groupList = []
            userPermList = []
        return render_to_response('vmUser/view_user.html',{"user":request.user,
                                                           "localtion":[{"name":"Home","url":'/'},
                                                                        {"name":"UserManage","url":'/usermanage/?op=list'}],
                                            "user":user,"permList":permList,"groupList":groupList,
                                            "userPermList":userPermList,"userGroupList":userGroupList},
                              context_instance=RequestContext(request))

    elif request.method == "POST":
        op = request.POST.get('op')
        if op in ['active','superuser','delete','modify']:
            try:
                user = User.objects.get(id=id)
            except:
                return JsonResponse({"code":500,"data":None,"msg":"Operation failed User does not exist"})
            if op == 'active':
                try:
                    user.is_active = int(request.POST.get('status'))
                    user.save()
                    return  JsonResponse({"code":200,"data":None,"msg":"Successful operation"})
                except:
                    return  JsonResponse({"code":500,"data":None,"msg":"User activation failed, user does not exist"})
            elif op == 'superuser':
                try:
                    user.is_superuser = int(request.POST.get('status'))
                    user.save()
                    return  JsonResponse({"code":200,"data":None,"msg":"Successful operation"})
                except:
                    return  JsonResponse({"code":500,"data":None,"msg":"User activation failed, user does not exist"})
            elif op == 'delete':
                try:
                    user.delete()
                    return  JsonResponse({"code":200,"data":None,"msg":"Successful operation"})
                except:
                    return  JsonResponse({"code":500,"data":None,"msg":"User deletion failed, user does not exist"})
            elif op == 'modify':
                try:
                    user.is_active = int(request.POST.get('is_active'))
                    user.is_superuser = int(request.POST.get('is_superuser'))
                    user.email = request.POST.get('email')
                    user.username = request.POST.get('username')
                    #If the permission key does not exist, clear the permissions
                    if request.POST.get('perm') is None:user.user_permissions.clear()
                    else:
                        userPermList = []
                        for perm in user.user_permissions.values():
                            userPermList.append(perm.get('id'))
                        permList = [ int(i) for i in request.POST.get('perm').split(',')]
                        addPermList = list(set(permList).difference(set(userPermList)))
                        delPermList = list(set(userPermList).difference(set(permList)))
                        #Add new permissions
                        for permId in addPermList:
                            perm = Permission.objects.get(id=permId)
                            User.objects.get(id=id).user_permissions.add(perm)
                        #Remove removed permissions
                        for permId in delPermList:
                            perm = Permission.objects.get(id=permId)
                            User.objects.get(id=id).user_permissions.remove(perm)
                    #Clear the user group if the user group key does not exist
                    if request.POST.get('group') is None:user.groups.clear()
                    else:
                        userGroupList = []
                        for group in user.groups.values():
                            userGroupList.append(group.get('id'))
                        groupList = [ int(i) for i in request.POST.get('group').split(',')]
                        addGroupList = list(set(groupList).difference(set(userGroupList)))
                        delGroupList = list(set(userGroupList).difference(set(groupList)))
                        #Add new user groups
                        for groupId in addGroupList:
                            group = Group.objects.get(id=groupId)
                            user.groups.add(group)
                        #Delete the removed user group
                        for groupId in delGroupList:
                            group = Group.objects.get(id=groupId)
                            user.groups.remove(group)
                    user.save()
                    return  JsonResponse({"code":200,"data":None,"msg":"Successful operation"})
                except Exception,e:
                    return  JsonResponse({"code":500,"data":e,"msg":"operation failed."})
        else:return  JsonResponse({"code":500,"data":None,"msg":"Unsupported operation or you do not have permission to operate this item."})
    else:return  JsonResponse({"code":500,"data":None,"msg":"Unsupported HTTP operations"})

@login_required
@permission_required('auth.change_user',login_url='/noperm/')
def user(request):
    if request.method == "GET":
        try:
            userList = User.objects.all()
        except Exception,e:
            userList = []
        return render_to_response('vmUser/user_manage.html',{"user":request.user,"localtion":[{"name":"Home","url":'/'},{"name":"UserManage","url":'/usermanage/?op=list'}],
                                            "userList":userList},
                              context_instance=RequestContext(request))
            
@login_required
@permission_required('auth.change_group',login_url='/noperm/')
def group(request):
    if request.method == "GET":
        permList = Permission.objects.all()
        try:
            groupList = []
            for group in  Group.objects.all():
                data = dict()
                data['id'] = group.id
                data['name'] = group.name
                permIdList = []
                #Get group permissions
                for perm in group.permissions.values():
                    permIdList.append(perm.get('id'))
                data['perm_id'] = permIdList
                groupList.append(data)
        except Exception,e:
            groupList = []
        return render_to_response('vmUser/group_manage.html',{"user":request.user,"localtion":[{"name":"Home","url":'/'},{"name":"UserGroupManage","url":'/groupmanage/?op=list'}],
                                            "groupList":groupList,"permList":permList},
                              context_instance=RequestContext(request))
    elif request.method == "POST":
        op = request.POST.get('op')
        if op == 'add' and request.user.has_perm('auth.add_group'):
            try:
                group = Group()
                group.name = request.POST.get('name')
                group.save()
                permList = [ int(i) for i in request.POST.get('perm').split(',')]
                for permId in permList:
                    perm = Permission.objects.get(id=permId)
                    group.permissions.add(perm)
                group.save()
                return  JsonResponse({"code":200,"data":None,"msg":"User group added successfully"})
            except Exception,e:
                print e
                return  JsonResponse({"code":500,"data":None,"msg":"User group failed to add"})
        if op in ['delete','modify'] and request.user.has_perm('VManagePlatform.change_group'):
            try:
                group = Group.objects.get(id=request.POST.get('id'))
            except:
                return JsonResponse({"code":500,"data":None,"msg":"Operation failed User group does not exist"})
            if op == 'delete':
                try:
                    group.delete()
                    return  JsonResponse({"code":200,"data":None,"msg":"Successful operation"})
                except:
                    return  JsonResponse({"code":500,"data":None,"msg":"User group deletion failed, user group does not exist"})
            elif op == 'modify':
                try:
                    group.name = request.POST.get('name')
                    #If the permission key does not exist, clear the permissions
                    if request.POST.get('perm') is None:group.permissions.clear()
                    else:
                        groupPermList = []
                        for perm in group.permissions.values():
                            groupPermList.append(perm.get('id'))
                        permList = [ int(i) for i in request.POST.get('perm').split(',')]
                        addPermList = list(set(permList).difference(set(groupPermList)))
                        delPermList = list(set(groupPermList).difference(set(permList)))
                        #Add new permissions
                        for permId in addPermList:
                            perm = Permission.objects.get(id=permId)
                            Group.objects.get(id=request.POST.get('id')).permissions.add(perm)
                        #Remove removed permissions
                        for permId in delPermList:
                            perm = Permission.objects.get(id=permId)
                            Group.objects.get(id=request.POST.get('id')).permissions.remove(perm)
                    group.save()
                    return  JsonResponse({"code":200,"data":None,"msg":"Successful operation"})
                except Exception,e:
                    return  JsonResponse({"code":500,"data":e,"msg":"operation failed."})
        else:return  JsonResponse({"code":500,"data":None,"msg":"Unsupported operation or you do not have permission to operate this item."})
    else:return  JsonResponse({"code":500,"data":None,"msg":"Unsupported HTTP operations"})
