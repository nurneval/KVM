## VManagePlatform nedir?
一 KVM Sanallaştırma yönetim platform

**Açık Kaynak Anlaşması**：[GNU General Public License v2](http://www.gnu.org/licenses/old-licenses/gpl-2.0.html)

**Açık kaynak bildirimi**：Herkese açık kaynak projem için star ya da fork atmaya izinlidir. Projenizdeki proje koduna başvurmanız gerekiyorsa, lütfen projedeki anlaşmayı ve telif hakkı bilgilerini bildirin.
## Geliştirme dilleri ve çerçeveleri
* Programlama dili：Python2.7 + HTML + JScripts
* Frontend Web frame：Bootstrap 
* Backend Web frame：Django  
* Backend task frame：Celery + Redis

## VManagePlatform Özellikleri nelerdir？

* Kvm Sanal makine üretim döngüsü yönetimi
    *  Kaynak kullanımı (örneğin: CPU, MEM, disk, ağ)
    *  Örnek kontrolü (örneğin: yaşam döngüsü yönetimi, anlık görüntü teknolojisi, Web Konsolu, vb.)
    *  Cihaz kaynak kontrolü (örneğin: hafızanın çevrimiçi ayarlanması, CPU kaynakları, sıcak ekleme?, sabit diski silme)
* Depolama havuzu yönetimi
    *  Ana depolama türlerini desteklemek için birimleri artırma veya azaltma
    *  Kaynak kullanımı
* Ağ yönetimi
    *  Destek SDN, temel ağ OpenVSwitch / Linux Bridge, IP adres tahsisi, ağ kartı trafiği kısıtlamaları vb. Kullanır.
* Kullanıcı yönetimi
    *  Destek kullanıcı hakları, kullanıcı grupları, kullanıcı sanal makine kaynak tahsisi, vb. 
* evsahibi
    *  Kaynak kullanımı，Örnek kontrolü

## Çevre gereksinimleri：
* Programlama dili：Python2.7 
* OS：CentOS 7 
* Ağ planlama：Yönetim Ağı Arayüzü=1，Sanal Veri Ağı>=1，Sadece bir ağ kartı kullanılıyorsa OpenVswitch Ağı kaybetmemek için ağı manuel olarak yapılandırmanız gerekir.
* SDN talep：OpenVswitch Or Linux Birdge

## TIPS：
* Kontrol Sunucusu: 1-10 adımı gerçekleştirin
* Düğüm Sunucusu: 2/3/4 adımları gerçekleştirin ve kontrol sunucusundaki 5. adımda ssh-copy-id dosyasını yürütün
* Daha iyi bir deneyim için Chrome veya Foxfire kullanmanız önerilir. Eğer sanal makine ipi almak istiyorsanız, lütfen sanal makineye qemu-guest-agent kurun (centos 6 libvirt> = 2.3.0 veya daha fazlasını yüklemek için ihtiyaç duyar)
* Ana makine listesi ve kullanıcı merkezi - sanal makinemin verileri güncellenir Görevlerin görev zamanlamasında yapılandırılması gerekir.

## Sanal makine ekleme işlemi:
* İlk adımda, platform ilk önce ana bilgisayarı (hesaplama düğümü) ekler. 
* İkinci adım, bir veri tipi depolama havuzu ve bir ayna depolama havuzu ekleyerek
	* Yansıtılmış depolama havuzu: Bilgi işlem düğümü bir dir tipi depolama havuzu ekler, ISO yansıma dosyasını depolama havuzuna yerleştirir veya ISO görüntü dosyasını bir NFS paylaşımına dönüştürebilir Bir depolama havuzu eklerken NFS modunu seçin. (Not: Sanal makine eklemek için sistem görüntüsüne yüklenebilir)
	* Veri depolama havuzu: Eklenecek sayfaya göre, esas olarak sanal makine sabit diskini depolamak için kullanılır.
* Üçüncü adım, bilgi işlem düğümleri ağ ekler, köprü ve nat modunu seçer
* Dördüncü adım, hesaplama düğümleri için sanal makineleri ayırmaktır
* Besinci adım, Bilgi İşlem Düğümlerinin VM Kaynak Bilgilerini Otomatik Olarak Güncelleştirmek için Görev Zamanlamasını Yapılandırma


## Kurulum ortamı yapılandırması</br>

İlk önce talep modülünü yapılandırın</br>
```
# yum install zlib zlib-devel readline-devel bzip2-devel openssl-devel gdbm-devel libdbi-devel ncurses-libs kernel-devel libxslt-devel libffi-devel python-devel libvirt libvirt-client libvirt-devel gcc git mysql-devel -y
# mkdir -p /opt/apps/ && cd /opt/apps/
# git clone https://github.com/welliamcao/VManagePlatform.git
# cd VManagePlatform
# sudo yum install epel-release && sudo yum install -y python-pip
# pip install -r requirements.txt
```
İkincisi, kvm'yi yükle
```
1. Güvenlik duvarını kapat selinux
# systemctl stop firewalld.service && systemctl disable firewalld.service
# setenforce 0 临时关闭
# systemctl stop NetworkManager
# systemctl disable NetworkManager


2. Kvm sanal makinesini kurun
# yum install python-virtinst qemu-kvm virt-viewer bridge-utils virt-top libguestfs-tools ca-certificates libxml2-python audit-libs-python device-mapper-libs 
# Servisi başlat
# systemctl start libvirtd
Not: Pencere sanal makinesini yüklemezseniz veya görüntüyü virtio sürücüsü ile kullanamıyorsanız. virtio-win-1.5.2-1.el6.noarch.rpm indir yüklenemedi ?
# rpm -ivh virtio-win-1.5.2-1.el6.noarch.rpm

Düğüm sunucusunun gerçekleştirmesi gerekmez
# yum -y install dnsmasq
# mkdir -p /var/run/dnsmasq/
```

Üçüncüsü, OpenVswitch'i kurun (Linux Bridge kullanarak temel ağ kullanırsanız yükleneniz gerekmez)
```
Openvswitch'i yükle
# yum install gcc make python-devel openssl-devel kernel-devel graphviz kernel-debug-devel autoconf automake rpm-build redhat-rpm-config libtool 
# cd ~
# wget http://openvswitch.org/releases/openvswitch-2.3.1.tar.gz
# tar xfz openvswitch-2.3.1.tar.gz
# mkdir -p ~/rpmbuild/SOURCES
# cp openvswitch-2.3.1.tar.gz rpmbuild/SOURCES
# sed 's/openvswitch-kmod, //g' openvswitch-2.3.1/rhel/openvswitch.spec > openvswitch-2.3.1/rhel/openvswitch_no_kmod.spec
# rpmbuild -bb --without check ~/openvswitch-2.3.1/rhel/openvswitch_no_kmod.spec
# yum localinstall /root/rpmbuild/RPMS/x86_64/openvswitch-2.3.1-1.x86_64.rpm
Python bağımlılık hatası varsa
# vim openvswitch-2.3.1/rhel/openvswitch_no_kmod.spec
BuildRequires: openssl-devel
Daha sonra ekle
AutoReq: no

# systemctl start openvswitch

```

Dördüncü olarak, Libvirt'i tcp bağlantısı kullan
```
# vim /etc/sysconfig/libvirtd
LIBVIRTD_CONFIG=/etc/libvirt/libvirtd.conf
LIBVIRTD_ARGS="--listen"

# vim /etc/libvirt/libvirtd.conf  #Sona eklendi
listen_tls = 0
listen_tcp = 1
tcp_port = "16509"
listen_addr = "0.0.0.0"
auth_tcp = "none"
# systemctl restart libvirtd 
```
Beşinci, SSH yapılandırın
```
# ssh-keygen -t  rsa
# ssh-copy-id -i ~/.ssh/id_rsa.pub  root@ipaddress
```

Altı, veritabanını yükleyin (MySQL, Redis)
```
MySQL'i kurun ve yapılandırın
# wget https://dev.mysql.com/get/mysql57-community-release-el7-9.noarch.rpm
# 	https://dev.mysql.com/downloads/repo/yum/ choose arch from here
# sudo rpm -ivh mysql57-community-release-el7-9.noarch.rpm
# yum install mysql-server mysql-client 
# systemctl start mysqld.service
# mysql -u root -p 
mysql> create database vmanage;
mysql> grant all privileges on vmanage.* to 'username'@'%' identified by 'userpasswd';
mysql>quit

Redis Kurulum ve yapılandırma
# wget http://download.redis.io/releases/redis-3.2.8.tar.gz
# tar -xzvf redis-3.2.8.tar.gz
# cd redis-3.2.8
# make
# make install
# vim redis.conf
daemonize yes
loglevel warning
logfile "/var/log/redis.log"
Sunucu ip adresinizi bağlayın
# cd ../
# mv redis-3.2.8 /usr/local/redis
# /usr/local/redis/src/redis-server /usr/local/redis/redis.conf
```

Yedi, Django'yu yapılandır
```
# cd /opt/apps/VManagePlatform/VManagePlatform/
# vim settings.py
7.1. BROKER_URL：Kendi adresinize geçin
7.2. DATABASES：
DATABASES = {
    'default': {
        'ENGINE':'django.db.backends.mysql',
        'NAME':'vmanage',
        'USER':'Kendi kurulum hesabınız',
        'PASSWORD':'Kendi ayar şifreniz',
        'HOST':'MySQLadresi'
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}
7.3. STATICFILES_DIRS
STATICFILES_DIRS = (
     '/opt/apps/VManagePlatform/VManagePlatform/static/',
    )
TEMPLATE_DIRS = (
#     os.path.join(BASE_DIR,'mysite\templates'),
    '/opt/apps/VManagePlatform/VManagePlatform/templates',
)
```

Sekiz, VManagePlatform veri sayfasını oluşturun
```
# cd /opt/apps/VManagePlatform/
# python manage.py migrate
# python manage.py createsuperuser
```
Dokuz, VManagePlatform'u başlat
```
# cd /opt/apps/VManagePlatform/
# python manage.py runserver youripaddr:8000
```

On, yapılandırma görev sistemi
```
# echo_supervisord_conf > /etc/supervisord.conf
# vim /etc/supervisord.conf
Sona eklendi
[program:celery-worker]
command=/usr/bin/python manage.py celery worker --loglevel=info -E -B  -c 2
directory=/opt/apps/VManagePlatform
stdout_logfile=/var/log/celery-worker.log
autostart=true
autorestart=true
redirect_stderr=true
stopsignal=QUIT
numprocs=1

[program:celery-beat]
command=/usr/bin/python manage.py celery beat
directory=/opt/apps/VManagePlatform
stdout_logfile=/var/log/celery-beat.log
autostart=true
autorestart=true
redirect_stderr=true
stopsignal=QUIT
numprocs=1

[program:celery-cam]
command=/usr/bin/python manage.py celerycam
directory=/opt/apps/VManagePlatform
stdout_logfile=/var/log/celery-celerycam.log
autostart=true
autorestart=true
redirect_stderr=true
stopsignal=QUIT
numprocs=1

启动celery
# /usr/local/bin/supervisord -c /etc/supervisord.conf
# supervisorctl status
```
## Yardım

VManagePlatform'un size yardımcı olabileceğini düşünüyorsanız, aşağıdaki şekillerde bağışta bulunabilirsiniz.！

![image](https://github.com/welliamcao/OpsManage/blob/master/demo_imgs/donate.png)

## İşlev ekranının bir parçası :
    Kullanıcı Merkezi
![](https://github.com/mafsin/VManagePlatform/raw/master/demo_images/user.png)</br>
    Giriş sayfası
![](https://github.com/mafsin/VManagePlatform/raw/master/demo_images/login.png)</br>
    Kullanıcı kaydı, giriş yapmak için yönetici aktivasyon gerektirir</br>
![](https://github.com/mafsin/VManagePlatform/raw/master/demo_images/register.png)</br>
    ev
![](https://github.com/mafsin/VManagePlatform/raw/master/demo_images/index.png)</br>
    Görev zamanlaması
![](https://github.com/mafsin/VManagePlatform/raw/master/demo_images/task.png)</br>
    Ana kaynaklar</br>
![](https://github.com/mafsin/VManagePlatform/raw/master/demo_images/server.png)</br>
    Sanal makine kaynakları</br>
![](https://github.com/mafsin/VManagePlatform/raw/master/demo_images/instance.png)</br>
    Web Console</br>
![](https://github.com/welliamcao/VManagePlatform/raw/master/demo_images/consle.png)</br>
    All instance list
![](https://github.com/mafsin/VManagePlatform/raw/master/demo_images/allinstances.png)</br>
