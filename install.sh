sudo apt update

# Install Git
sudo apt install -y git
git config --global user.name "Simon"
git config --global user.email "Simon.meersschaut@gmail.com"

# Clone git repository
git clone "https://github.com/SimonMeersschaut/earlybird-os.git"
cd earlybird-os

# Install Libraries
sudo apt install -y \
  libatk1.0-0 \
  libatk-bridge2.0-0 \
  libgtk-3-0 \
  libnss3 \
  libxss1 \
  libasound2 \
  libxtst6 \
  libx11-xcb1 \
  libgbm1 \
  xorg \
  python3-pytest # for when you're not in a venv

# Libraries for input drivers (Touch screen)
sudo apt install -y \
  xserver-xorg-input-evdev \
  xserver-xorg-input-libinput

# Install python packages
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# for hiding the mouse
sudo apt install -y unclutter
sudo apt install -y chromium-browser

./deploy/services.sh

sudo cp deploy/Xwrapper.config /etc/X11/

# Install OLLama
curl -fsSL https://ollama.com/install.sh | sh

