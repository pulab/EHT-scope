// manually control EHT lights and camera focus.
// also accept input from serial port when in serial mode
// serial commands:
//   ID__ -- arduino returns "EHTarduino"
//   RUN_XXXX -- arduino turns on white light and pulses blue light at XXXX rate
//   STOP -- arduino stops pacing and turns off white light
//   WHIT -- arduino 
//   F_UPXXXX -- camera up XXXX amt
//   F_DNXXXX -- camera down XXXX amt


#include <Adafruit_MCP4725.h>

#include <Adafruit_RGBLCDShield.h>    // RGB shield with buttons
#include <Servo.h>                    // focus motor
#include <Adafruit_NeoPixel.h>        // Neopixel

#include <EEPROM.h>                   // store values in EEPROM

// These #defines are for the backlight color
#define OFF 0x0
#define RED 0x1
#define YELLOW 0x3
#define GREEN 0x2
#define TEAL 0x6
#define BLUE 0x4
#define VIOLET 0x5
#define WHITE 0x7 

#define TERM '\r'
#define TIMEOUT 2000 // serial timeout in ms
#define LED_COUNT 16
#define NEOPIXEL_ON 1
#define NEOPIXEL_OFF 0
#define FOCUS_addr_hi 0 // address to write focus value (2 bytes).
#define FOCUS_addr_lo 1

Adafruit_RGBLCDShield lcd = Adafruit_RGBLCDShield(); // lcd object for the lcd i2c shield, which has 5 buttons on it.
Servo myservo;                                        // create servo object for focus motor

const int NEOPIXEL = 5; // pin 5 for white LED --5,6 have higher PWM frequency
//const int WHITE_LED = 5
const int BLUE_LED = 6; // pin 6 for blue LED
const int FOCUS = 10; // pin 10 for focus actuator
const int FRAME_TRIGGER = 2; // pin 2 to trigger camera
const int FRAME_TRIGGER_WIDTH = 2; // 2 ms TTL width

// Declare our NeoPixel strip object:
Adafruit_NeoPixel strip(LED_COUNT, NEOPIXEL, NEO_RGBW + NEO_KHZ800);
// Argument 1 = Number of pixels in NeoPixel strip
// Argument 2 = Arduino pin number (most are valid)
// Argument 3 = Pixel type flags, add together as needed:
//   NEO_KHZ800  800 KHz bitstream (most NeoPixel products w/WS2812 LEDs)
//   NEO_KHZ400  400 KHz (classic 'v1' (not v2) FLORA pixels, WS2811 drivers)
//   NEO_GRB     Pixels are wired for GRB bitstream (most NeoPixel products)
//   NEO_RGB     Pixels are wired for RGB bitstream (v1 FLORA pixels, not v2)
//   NEO_RGBW    Pixels are wired for RGBW bitstream (NeoPixel RGBW products)

String mode = "Serial"; // start in Serial mode
int menuSelection = 0;
char *menuItems[] = { "Run", "Rate", "Focus", "White On", "White Int", "Blue Int", "Blue PW","Serial","Sleep"};
int menuItemsLength=9;
int rate = 120; // set default to 120 bpm
const int increment = 10; // increment rate by 10
const int minRate = 30;
const int maxRate = 240;
int pulseWidth = 8; // width for pacing pulse in msec
int whiteIntensity = 100; // default for white intensity (in % of max)
int blueIntensity = 100; // default for blue intensity (in % of max)
unsigned int paceTime = 60000/rate; // wait time between beats in, based on 60000/bpm
unsigned long lastPaceTime=0;
boolean paceState=false;
int paceInterval; // interval to wait for pacer to change state, either paceTime or pulseWidth
unsigned int frameTime = 40; // wait time between image frames = 25 fps
unsigned long lastFrameTime=0;
int servoPosition; // starting servo position in microseconds
int minServoPosition=1500;
int maxServoPosition=1760;

String msg, cmd;
boolean serialRun=false;
int value;
int delta;

void setup() {
  Serial.begin(9600);
  Serial.setTimeout(TIMEOUT);
  strip.begin();                                      // initialize NeoPixel strip object
  strip.show();                                       // turn OFF all pixels
  neoPixelIntensity(whiteIntensity);
  pinMode(BLUE_LED, OUTPUT);
  pinMode(FRAME_TRIGGER, OUTPUT);

  lcd.begin(16, 2);
  displayMenu();

  myservo.attach(FOCUS); // attach the servo to the FOCUS pin
  myservo.writeMicroseconds(servoPosition);

  servoPosition = constrain(EEPROM.read(FOCUS_addr_hi)*16 + EEPROM.read(FOCUS_addr_lo),minServoPosition,maxServoPosition);
}

void loop() {

  uint8_t buttons = lcd.readButtons(); // read buttons

  if (mode=="TOP_MENU") {
    if (buttons) {
      if (buttons & BUTTON_UP) {
        menuSelection--;
        if (menuSelection<0)
          menuSelection = menuItemsLength-1;
      } else if (buttons & BUTTON_DOWN) { 
        menuSelection++;
        if (menuSelection >= menuItemsLength)
          menuSelection = 0;
      } else if (buttons & BUTTON_SELECT) {
        mode=menuItems[menuSelection];
        if (mode=="White On" || mode == "White Int" || mode=="Focus" || mode == "Run") {
          neoPixel(NEOPIXEL_ON);
          lastPaceTime=millis();
          paceState=false;
          lastFrameTime=millis();
          paceTime=60000/rate;
          paceInterval=paceTime;
        }
      }
      displayMenu();
      delay(300);
    }
  } else if (mode=="Rate") {
    if (buttons) {
      if (buttons & BUTTON_UP) {
        rate += increment;
        rate = constrain(rate,minRate,maxRate);
      } else if (buttons & BUTTON_DOWN) {
        rate -= increment;
        rate = constrain(rate,minRate,maxRate);
      } else if (buttons & BUTTON_SELECT) {
        mode="TOP_MENU";
      }
      displayMenu();
      delay(300);
    }
  } else if (mode=="Run") {
    if (buttons) {  // exit run on any button press
      neoPixel(NEOPIXEL_OFF);             // turn lights off
      digitalWrite(BLUE_LED,LOW);
      mode="TOP_MENU";
      displayMenu();
      delay(300);
    } else {
      if (millis()-lastPaceTime>paceInterval) {   // blue light pacemaker
        lastPaceTime=millis();
        if (paceState) {    // currently on, turn off
          digitalWrite(BLUE_LED,LOW);
          paceInterval=paceTime;
          paceState=false;
        } else {            // currently off, turn on
          analogWrite(BLUE_LED,map(blueIntensity,0,100,0,255));
          paceInterval=pulseWidth;
          paceState=true;
        }
      }
      if (millis()-lastFrameTime>frameTime) {   // trigger camera frame -- although not currently used for camera control
        lastFrameTime=millis();
        digitalWrite(FRAME_TRIGGER, HIGH);
        delay(FRAME_TRIGGER_WIDTH);                               // camera TTL pulse width
        digitalWrite(FRAME_TRIGGER, LOW);
      }
    }
  } else if (mode=="White On") {
    if (buttons) {
      neoPixel(NEOPIXEL_OFF);
      mode="TOP_MENU";
      displayMenu();
      delay(300);
    }
  } else if (mode=="Focus") {
    if (buttons) {
      if (buttons & BUTTON_UP) {
        servoPosition+=10;
      } else if (buttons & BUTTON_DOWN) {
        servoPosition-=10;
      } else if (buttons & BUTTON_SELECT) {
        myservo.writeMicroseconds(servoPosition-200);
        delay(1000);
        myservo.writeMicroseconds(servoPosition);
        mode = "TOP_MENU";
        neoPixel(NEOPIXEL_OFF);
        mode="TOP_MENU";
      } else if (buttons & BUTTON_RIGHT) {
        myservo.writeMicroseconds(servoPosition-200);
        delay(1000);
        myservo.writeMicroseconds(servoPosition);
      }
      servoPosition=constrain(servoPosition,minServoPosition,maxServoPosition);
      saveFocus(servoPosition); // write to EEPROM
      displayMenu();
    }
  } else if (mode=="Serial") {                        // handle serial commands
    if (Serial.available() > 0) {
      msg = Serial.readStringUntil(TERM);
      msg.trim();
      cmd = msg.substring(0,4);
      if (msg.length() > 4) {
        value=msg.substring(4).toInt();
        Serial.println(value);
        }
      if (cmd == "IDaa") {
        Serial.println("EHT");
      } else if (cmd == "WHIT")
        neoPixel(NEOPIXEL_ON);
      else if (cmd == "STOP") {
        neoPixel(NEOPIXEL_OFF);
        serialRun=false;
        digitalWrite(BLUE_LED,LOW);
        displayMenu();      
      } else if (cmd == "FaUP" || cmd == "FaDN") {
        if (cmd == "FaUP")
          servoPosition+=value;
        else
          servoPosition-=value;
        servoPosition=constrain(servoPosition,minServoPosition,maxServoPosition);
        myservo.writeMicroseconds(servoPosition-200);
        delay(1000);
        myservo.writeMicroseconds(servoPosition);        
      } else if (cmd == "RUNa") {
          serialRun=true;
          lcd.clear();
          lcd.setBacklight(RED);
          lcd.print("Serial run");
          lcd.setCursor(0,1);
          rate=value;
          lcd.print(String(rate)+"  ");
          neoPixel(NEOPIXEL_ON);              // white light on
          lastPaceTime=millis();
          paceTime=60000/rate;
      } else {
        Serial.println(cmd);
      }
    } else if (buttons) {                     // exit serial mode
      mode="TOP_MENU";
      serialRun=false;
      neoPixel(NEOPIXEL_OFF);                 // lights off
      digitalWrite(BLUE_LED,LOW);
      displayMenu();  
    } else if (serialRun) {
      if (millis()-lastPaceTime>paceInterval) {   // blue light pacemaker
        lastPaceTime=millis();
        if (paceState) {    // currently on, turn off
          digitalWrite(BLUE_LED,LOW);
          paceInterval=paceTime;
          paceState=false;
        } else {            // currently off, turn on
          analogWrite(BLUE_LED,map(blueIntensity,0,100,0,255));
          paceInterval=pulseWidth;
          paceState=true;
        }
      }
      if (millis()-lastFrameTime>frameTime) {   // trigger camera frame
        lastFrameTime=millis();
        digitalWrite(FRAME_TRIGGER, HIGH);
        delay(FRAME_TRIGGER_WIDTH);                               // camera TTL pulse width
        digitalWrite(FRAME_TRIGGER, LOW);
      }
    }
  } else if (mode=="Blue Int") {        // blue intensity
    if (buttons) {
      if (buttons & BUTTON_UP) {
        blueIntensity+=10;
      } else if (buttons & BUTTON_DOWN) {
        blueIntensity-=10;
      } else if (buttons & BUTTON_SELECT) {
        mode="TOP_MENU";
      }
      delay(300);
      blueIntensity=constrain(blueIntensity, 10, 100);
      displayMenu();
    }
  } else if (mode=="White Int") {        // blue intensity
    if (buttons) {
      if (buttons & BUTTON_UP) {
        whiteIntensity+=10;
      } else if (buttons & BUTTON_DOWN) {
        whiteIntensity-=10;
      } else if (buttons & BUTTON_SELECT) {
        neoPixelIntensity(whiteIntensity);
        mode="TOP_MENU";
      }
      delay(300);
      whiteIntensity=constrain(whiteIntensity, 10, 100);
      neoPixelIntensity(whiteIntensity);
      if (mode=="TOP_MENU")
        neoPixel(NEOPIXEL_OFF);
      else
        neoPixel(NEOPIXEL_ON);
      displayMenu();
    }
  } else if (mode=="Blue PW") {       // blue pulse width
    delta=pulseWidth/5;
    if (buttons) {
      if (buttons & BUTTON_UP) {
        pulseWidth+=delta;
      } else if (buttons & BUTTON_DOWN) {
        pulseWidth-=delta;
      } else if (buttons & BUTTON_SELECT) {
        mode="TOP_MENU";
      }
      delay(300);
      pulseWidth=constrain(pulseWidth, 5, 50);
      displayMenu();
    }
  } else if (mode=="Sleep") {         // turn off lcd and wait for button
    lcd.noDisplay();                  // wait here until keypress
    lcd.setBacklight(OFF);
    while (!lcd.readButtons())
       delay(1000);
    lcd.display();
    mode="TOP_MENU";
    menuSelection=0;
    displayMenu();
    delay(300);
    buttons=lcd.readButtons();
  }
}

void displayMenu() {
  lcd.clear();
  lcd.setBacklight(BLUE);
  lcd.setCursor(0,0);
  if (mode=="TOP_MENU") {
    lcd.print("UpDn SEL=Select");
    lcd.setCursor(0,1);
    lcd.print(menuItems[menuSelection]);
  } else if (mode=="Run") {
    lcd.setBacklight(RED);
    lcd.print("RUN  bttn to stop");
    lcd.setCursor(0,1);
    lcd.print(String(rate)+"  ");
  } else if (mode=="Rate") {
    lcd.print("Rate UpDn=chg");
    lcd.setCursor(0,1);
    lcd.print(String(rate)+" bpm  SEL=set");
  } else if (mode=="White On") {
    lcd.print("White Light");
    lcd.setCursor(0,1);
    lcd.print("Bttn to stop");
  } else if (mode=="Focus") {
    lcd.print("Focus UpDn=chg");
    lcd.setCursor(0,1);
    lcd.print(String(servoPosition)+" Fwd=try SEL");
  } else if (mode=="Serial") {
    lcd.setBacklight(GREEN);
    lcd.print("Serial port");
    lcd.setCursor(0,1);
    lcd.print("Bttn to stop");
  } else if (mode=="Blue Int") {
    lcd.print("Blue Int UpDn=chg");
    lcd.setCursor(0,1);
    lcd.print(String(blueIntensity)+"   SEL=set");
  } else if (mode == "White Int") {
    lcd.print("White Int UpDn=chg");
    lcd.setCursor(0,1);
    lcd.print(String(whiteIntensity)+"  SEL=set");
  } else if (mode=="Blue PW") {
    lcd.print("Blue PW UpDn=chg");
    lcd.setCursor(0,1);
    lcd.print(String(pulseWidth)+"   SEL=set");
  } else if (mode=="Sleep") {
    lcd.print("Sleep");
    lcd.setCursor(0,1);
    lcd.print("Key to wake");
    delay(5000);
  } else {
    lcd.print("Error: bad mode");
    lcd.setCursor(0,1);
    lcd.print(mode);
  }
}

void neoPixel(int OnFlag) {                  // neoPixel white if OnFlag=1, black otherwise.
uint32_t color;
  if (OnFlag==NEOPIXEL_ON) {
    color=strip.Color(0,0,0,255);
  } else {
    color=strip.Color(0,0,0,0);
  }
  for (int i=0;i<strip.numPixels(); i++) {
    strip.setPixelColor(i,color);
    strip.show();
  }
}

void neoPixelIntensity(int value) {         // value % max intensity 0 to 100
  strip.setBrightness(map(value,0,100,0,255));
}

void saveFocus(int dec) {                   // save focus value to EEPROM
  EEPROM.write(FOCUS_addr_lo,dec % 16);
  EEPROM.write(FOCUS_addr_hi,dec / 16);
}
