# -*- mode: ruby -*-
# vi: set ft=ruby :

# Vagrantfile API/syntax version. Don't touch unless you know what you're doing!
VAGRANTFILE_API_VERSION = "2"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
  config.vm.hostname = "sdnalyzer"
  config.vm.box = "ubuntu/trusty64"
  
  config.vm.network "forwarded_port", host: 54320, guest: 5432
  config.vm.network "forwarded_port", host: 554, guest: 554
  config.vm.network "forwarded_port", host: 8080, guest: 80
  config.vm.network "forwarded_port", host: 8090, guest: 8080

  config.vm.network "forwarded_port", host: 4711, guest: 4711
  config.vm.network "forwarded_port", host: 4712, guest: 4712
  config.vm.network "forwarded_port", host: 4713, guest: 4713
  
  config.vm.provider "virtualbox" do |vb|
	vb.name = "sdnalyzer"
	vb.cpus = 1
	vb.memory = 1024
	vb.gui = false
  end

end
