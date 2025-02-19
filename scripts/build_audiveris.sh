#!/bin/bash

# Check for Java
if ! command -v java &> /dev/null; then
	echo "Java not found. Installing OpenJDK 17..."
	sudo apt update
	sudo apt install -y openjdk-17-jdk
fi

# Check for Git
if ! command -v git &> /dev/null; then
	echo "Git not found. Installing..."
	sudo apt install -y git
fi

# Create external directory if it doesn't exist
EXTERNAL_DIR="$(dirname "$(dirname "$0")")/external"
mkdir -p "$EXTERNAL_DIR"
cd "$EXTERNAL_DIR"

# Clone Audiveris if not already cloned
if [ ! -d "audiveris" ]; then
	echo "Cloning Audiveris..."
	git clone https://github.com/Audiveris/audiveris.git
else
	echo "Audiveris repository already exists. Updating..."
	cd audiveris
	git pull
	cd ..
fi

cd audiveris

# Create libs directory
mkdir -p libs
cd libs

# Download JAI libraries
echo "Downloading JAI libraries..."
wget -O jai-1_1_3-lib-linux-amd64.tar.gz https://download.java.net/media/jai/builds/release/1_1_3/jai-1_1_3-lib-linux-amd64.tar.gz
tar xf jai-1_1_3-lib-linux-amd64.tar.gz
cp jai-1_1_3/lib/jai_core.jar .
cp jai-1_1_3/lib/jai_codec.jar .
rm -rf jai-1_1_3 jai-1_1_3-lib-linux-amd64.tar.gz

cd ..

# Build Audiveris
echo "Building Audiveris..."
./gradlew build -x test --no-daemon --info

# Export environment variable
echo "export AUDIVERIS_PATH=\"$EXTERNAL_DIR/audiveris\"" >> ~/.bashrc
source ~/.bashrc

echo "Audiveris build complete!"
echo "AUDIVERIS_PATH has been set to: $EXTERNAL_DIR/audiveris"