#!/usr/bin/env python  
# _#_ coding:utf-8 _*_  
from django.db import models


class VmServer(models.Model):
    server_ip = models.GenericIPAddressField(unique=True,verbose_name='ManagementIP')
    username = models.CharField(max_length=100,verbose_name='username')
    passwd = models.CharField(max_length=100,blank=True,null=True,verbose_name='password')
    hostname = models.CharField(max_length=100,blank=True,null=True,verbose_name='Hostname')
    instance = models.SmallIntegerField(blank=True,null=True,verbose_name='Instance') 
    vm_type =  models.IntegerField(verbose_name='VMType')
    mem = models.CharField(max_length=100,blank=True,null=True,verbose_name='MemoryCapacity')
    cpu_total = models.SmallIntegerField(blank=True,null=True,verbose_name='CPUNumber') 
    status =  models.SmallIntegerField(blank=True,null=True,verbose_name='Status')
    createTime = models.DateTimeField(auto_now_add=True,blank=True,null=True)
    modifyTime = models.DateTimeField(auto_now=True,blank=True,null=True)
    class Meta:
        permissions = (
            ("read_vmserver", "Can read Virtual host information"),
        )
        verbose_name = 'Virtual host information'  
        verbose_name_plural = 'Virtual host information'


class VmDHCP(models.Model):
    mode = models.CharField(unique=True,max_length=100,verbose_name='dhcpType')
    drive = models.CharField(max_length=10,verbose_name='DriveType')
    brName = models.CharField(max_length=100,verbose_name='BridgeName')
    server_ip = models.GenericIPAddressField(verbose_name='DHCPServiceAddress')
    ip_range = models.CharField(max_length=100,verbose_name='AddressPool')
    gateway = models.GenericIPAddressField(blank=True,null=True,verbose_name='GatewayAddress')
    dns = models.GenericIPAddressField(blank=True,null=True,verbose_name='DNSAddress') 
    dhcp_port = models.CharField(max_length=100,verbose_name='dhcpPortName')
    isAlive = models.SmallIntegerField(default=1,null=True, blank=True,verbose_name='ActivateNow') 
    status = models.SmallIntegerField(default=1,null=True, blank=True,verbose_name='WhethertoStart') 
    createTime = models.DateTimeField(auto_now_add=True,blank=True,null=True)
    modifyTime = models.DateTimeField(auto_now=True,blank=True,null=True)
    class Meta:
        permissions = (
            ("read_vmdhcp", "Can read Virtual Host DHCP Configuration"),
        )
        verbose_name = 'Virtual Host DHCP Configuration'  
        verbose_name_plural = 'Virtual Host DHCP Configuration'
        unique_together = (("mode", "brName"))

class VmInstance_Template(models.Model):
    name =  models.CharField(unique=True,max_length=100,verbose_name='TemplateName')
    cpu =  models.SmallIntegerField(verbose_name='cpuNumber')
    mem =  models.SmallIntegerField(verbose_name='memSize')
    disk =  models.SmallIntegerField(verbose_name='DiskSize') 
    class Meta:
        permissions = (
            ("read_vminstance_template", "Can read Virtual Host Template"),
        )
        verbose_name = 'Virtual Host Template'  
        verbose_name_plural = 'Virtual Host Template'
        
        
class VmServerInstance(models.Model):  
    server = models.ForeignKey('VmServer') 
    name =  models.CharField(max_length=100,verbose_name='InstanceName')
    cpu = models.SmallIntegerField(verbose_name='CpuNumber')
    mem = models.IntegerField(verbose_name='MemoryCapacity')
    status = models.SmallIntegerField(verbose_name='InstanceStatus')
    owner =  models.CharField(max_length=50,blank=True,null=True,verbose_name='Owner')
    rate_limit = models.SmallIntegerField(blank=True,null=True,verbose_name='NICLimit')
    token = models.CharField(max_length=100,blank=True,null=True,verbose_name='Token')
    ips = models.TextField(max_length=200,blank=True,null=True,verbose_name='ipAddress')
    vnc = models.SmallIntegerField(blank=True,null=True,verbose_name='VNCPort')
    class Meta:
        permissions = (
            ("read_vmserver_instance", "Can read Virtual host instance"),
        )
        verbose_name = 'Virtual host instance'  
        verbose_name_plural = 'Virtual host instance'  
    unique_together = (("server", "name"))    
        

        
class VmLogs(models.Model): 
    server_id = models.IntegerField(verbose_name='Hostid',blank=True,null=True,default=None)
    vm_name = models.CharField(max_length=50,verbose_name='VMName',default=None)
    content = models.CharField(max_length=100,verbose_name='OpContent',default=None)
    user =  models.CharField(blank=True,null=True,max_length=20,verbose_name='User')
    status = models.SmallIntegerField(verbose_name='ResultOf',blank=True,null=True) 
    isRead = models.SmallIntegerField(verbose_name='IsRead',blank=True,null=True) 
    result = models.TextField(verbose_name='Reason',blank=True,null=True) 
    create_time = models.DateTimeField(auto_now_add=True,blank=True,null=True,verbose_name='CreationTime')
    class Meta:
        permissions = (
            ("read_vmlogs", "Can read Virtual host operation log"),
        )
        verbose_name = 'Virtual host operation log'  
        verbose_name_plural = 'Virtual host operation log' 