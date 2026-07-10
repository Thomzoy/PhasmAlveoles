export BUILD_DIR=$(pwd)

git clone https://github.com/v923z/micropython-ulab.git ulab
git clone https://github.com/micropython/micropython.git

cd $BUILD_DIR/micropython/

git clone -b v5.4.2 --recursive https://github.com/espressif/esp-idf.git

