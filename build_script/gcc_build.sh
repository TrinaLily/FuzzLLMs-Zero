#/bin/sh
# Remember to install flex lcov: apt-get install lcov flex
# this script is to build gcc with coverage option
apt-get install lcov flex

cd ../target/gcc/
git clone git://gcc.gnu.org/git/gcc.git ./gcc-13
cd ./gcc-13/
git checkout releases/gcc-13.1.0
./contrib/download_prerequisites

mkdir ../gcc-coverage-build
cd ..

# Get current directory absolute path, then build GCC installation path
CURRENT_DIR=$(pwd)
GCC_INSTALL_PREFIX="$CURRENT_DIR/GCC-13-COVERAGE"
cd ./gcc-coverage-build
./../gcc-13/configure --enable-languages=c,c++ --prefix="$GCC_INSTALL_PREFIX" --enable-coverage --disable-multilib

make -j
make install
