sudo apt install libxml2-utils
sudo apt install -y openjdk-11-jdk
#The JDK will be installed to /usr/lib/jvm/java-11-openjdk-amd64/. Please manually verify the installation path. If it is not installed at this location, please modify the compile.sh script located in FuzzLLMs-Zero/target/java and update the JAVA_HOME variable to the actual installation path.