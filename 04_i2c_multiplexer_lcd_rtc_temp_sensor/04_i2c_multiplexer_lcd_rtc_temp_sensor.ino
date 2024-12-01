// I2C Connections (RTC, LCD)
// Mulitplexer to support multiple I2C devices: AZDelivery PCA9548A I2C 8-Channel Multiplexer (https://www.amazon.de/-/en/AZDelivery-PCA9548A-Multiplexer-8-Channel-Compatible/dp/B086W7SL63)
#include <Wire.h>

// SPI Connections (Micro SD Card Module)
#include <SPI.h>

// Micro SD Card Module (SPI): AZDelivery SPI Reader Micro Memory SD TF Card Memory Card Shield Module (https://www.az-delivery.de/en/products/copy-of-spi-reader-micro-speicherkartenmodul-fur-arduino)
#include <SD.h>

// Date and time (I2C): DS1307 RTC
#include <RTClib.h>
// installed RTClib from Adafruit (https://github.com/adafruit/RTClib)

// Temperature and humidity (PIN): DHT11
#include <SimpleDHT.h>
// installed: 'SimpleDHT' v1.0.15 from Winlin (https://github.com/winlinvip/SimpleDHT/tree/1.0.15)

// LCD (I2C): SunFounder I2C TWI Serial 2004 LCD Module Shield (4 rows, 20 columns)
#include <LiquidCrystal_I2C.h>
// installed: 'LiquidCrystal I2C' v1.1.2 from Frank de Brabander (https://github.com/johnrickman/LiquidCrystal_I2C/tree/1.1.2)

constexpr int PIN_BUTTON_LCD_BACKLIGHT_TOGGLE = 7;
constexpr int PIN_BUTTON_RESET_ERR = 5;
constexpr int PIN_BUTTON_USE_SD_TOGGLE = 8;
constexpr int PIN_DHT_11 = 2;
constexpr int PIN_SD_CARD_SELECT_LOGS = 10;
constexpr int PIN_LED_ERROR = 3;
constexpr int PIN_LED_SD_ON = 6;

constexpr uint8_t I2C_ADDRESS_LCD = 0x27;
constexpr uint8_t I2C_ADDRESS_MULTIPLEXER_TCA9548A = 0x70;

constexpr uint8_t LCD_COLS = 20;
constexpr uint8_t LCD_ROWS = 4;

constexpr int LOOP_DELAY = 100;
constexpr int BUTTON_DEBOUNCE_DELAY_MS = 500;

/** DHT11 sampling rate is 1HZ = 1s = 1000ms */
constexpr int DHT11_SAMPLE_RATE_DELAY_MS = 2 * 1000;
constexpr int RTC_SAMPLE_RATE_DELAY_MS = 1000;

constexpr uint8_t MULTIPLEXER_TCA9548A_I2C_CHANNEL_LCD = 0;
constexpr uint8_t MULTIPLEXER_TCA9548A_I2C_CHANNEL_TIME = 1;

constexpr const char* FILENAME_SD_CARD_LOGS_CSV = "TEMP.CSV";
constexpr const char* CSV_HEADER_SD_CARD_LOGS_CSV = "TimeUTC,TemperatureCelsius,RelativeHumidity";

constexpr bool ENABLE_SD_CARD_LOGGING = true;
constexpr bool ENABLE_RTC = true;
constexpr bool ENABLE_LCD = true;

// TODO: Then SD Card code crashes the arduino, set to 1 to experience pain
#define ENABLE_SD_CARD 0

// SimpleDHT(int pin);
SimpleDHT11 dht11(PIN_DHT_11);

// LiquidCrystal_I2C(uint8_t lcd_Addr, uint8_t lcd_cols, uint8_t lcd_rows)
LiquidCrystal_I2C lcd(I2C_ADDRESS_LCD, LCD_COLS, LCD_ROWS);

RTC_DS1307 rtc;

constexpr const char* daysOfTheWeek[7] = {
  "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"
};

void setTCAChannel(uint8_t channel) {
  Wire.beginTransmission(I2C_ADDRESS_MULTIPLEXER_TCA9548A);
  Wire.write(1 << channel);
  Wire.endTransmission();
}

void testChannel(uint8_t channel) {
  setTCAChannel(channel);
  Serial.print("Testing channel: ");
  Serial.println(channel);
  for (uint8_t address = 1; address < 127; ++address) {
    Wire.beginTransmission(address);
    if (Wire.endTransmission() == 0) {
      Serial.print("I2C device found at: 0x");
      Serial.println(address, HEX);
    }
  }
}

bool backlightOn = false;
bool sdOn = false;
bool sdInitalized = false;

void setup() {
  // init serial connection
  Serial.begin(115200);
  Serial.println("Setup...");
  // init buttons
  pinMode(PIN_BUTTON_LCD_BACKLIGHT_TOGGLE, INPUT_PULLUP);
  pinMode(PIN_BUTTON_RESET_ERR, INPUT_PULLUP);
  pinMode(PIN_BUTTON_USE_SD_TOGGLE, INPUT_PULLUP);
  // init error LED
  pinMode(PIN_LED_ERROR, OUTPUT);
  digitalWrite(PIN_LED_ERROR, LOW);
  // init sd indicator LED
  pinMode(PIN_LED_SD_ON, OUTPUT);
  digitalWrite(PIN_LED_SD_ON, sdOn ? HIGH : LOW);
  // init multiplexer
  Wire.begin();
  Serial.println("Scanning I2C channels...");
  for (uint8_t channel = 0; channel < 8; ++channel) {
    testChannel(channel);
  }
  Serial.println("Ended scan.");
  // init lcd display
  if constexpr (ENABLE_LCD) {
    setTCAChannel(MULTIPLEXER_TCA9548A_I2C_CHANNEL_LCD);
    lcd.init();
    lcd.clear();
    lcd.setBacklight(static_cast<uint8_t>(backlightOn));
  }
  // init RTC
  if constexpr (ENABLE_RTC) {
    setTCAChannel(MULTIPLEXER_TCA9548A_I2C_CHANNEL_TIME);
    if (!rtc.begin()) {
      digitalWrite(PIN_LED_ERROR, HIGH);
      Serial.println("ERROR: Could not find RTC");
    } else if (!rtc.isrunning()) {
      Serial.println("ERROR: RTC is not running, set time");
      // When time needs to be set on a new device, or after a power loss, the
      // following line sets the RTC to the date & time this sketch was compiled
      rtc.adjust(DateTime(F(__DATE__), F(__TIME__)));
      // This line sets the RTC with an explicit date & time, for example to set
      // January 21, 2014 at 3am you would call:
      // rtc.adjust(DateTime(2014, 1, 21, 3, 0, 0));
    }
  }

  Serial.println("Setup complete.");
}

unsigned long previousMillisDHT11 = 0;
unsigned long previousMillisRTC = 0;

int previousTemperature = 0;
int previousHumidity = 0;

void loop() {
  if (digitalRead(PIN_BUTTON_RESET_ERR) == LOW) {
    digitalWrite(PIN_LED_ERROR, LOW);
    Serial.println("Reset error indicator");
    delay(BUTTON_DEBOUNCE_DELAY_MS);
  }

  if (digitalRead(PIN_BUTTON_USE_SD_TOGGLE) == LOW) {
    sdOn = !sdOn;
    digitalWrite(PIN_LED_SD_ON, sdOn ? HIGH : LOW);
    Serial.print("Toogle SD ");
    Serial.println(sdOn ? "ON" : "OFF");
    delay(BUTTON_DEBOUNCE_DELAY_MS);
  }

  // toggle backlight when button is pressed
  if (digitalRead(PIN_BUTTON_LCD_BACKLIGHT_TOGGLE) == LOW) {
    backlightOn = !backlightOn;
    Serial.print("Toggle LCD Display backlight backlightOn=");
    Serial.println(backlightOn ? "true" : "false");
    if constexpr (ENABLE_LCD) {
      setTCAChannel(MULTIPLEXER_TCA9548A_I2C_CHANNEL_LCD);
      lcd.setBacklight(static_cast<uint8_t>(backlightOn));
    }
    delay(BUTTON_DEBOUNCE_DELAY_MS);
  }

  unsigned long currentMillis = millis();

  // get current temperature and humidity
  float temperature = 0;
  float humidity = 0;
  bool tempChangeDetected = false;
  if (currentMillis - previousMillisDHT11 >= DHT11_SAMPLE_RATE_DELAY_MS) {
    previousMillisDHT11 = currentMillis;
    int err = SimpleDHTErrSuccess;
    // int read2(float* ptemperature, float* phumidity, byte pdata[40])
    if ((err = dht11.read2(&temperature, &humidity, NULL)) != SimpleDHTErrSuccess) {
      digitalWrite(PIN_LED_ERROR, HIGH);
      Serial.print("Read DHT11 failed, err=");
      Serial.print(SimpleDHTErrCode(err));
      Serial.print(",");
      Serial.println(SimpleDHTErrDuration(err));
      digitalWrite(PIN_LED_ERROR, HIGH);
    } else {
      if (static_cast<int>(temperature) != previousTemperature) {
        previousTemperature = static_cast<int>(temperature);
        tempChangeDetected = true;
      }
      if (static_cast<int>(humidity) != previousHumidity) {
        previousHumidity = static_cast<int>(humidity);
        tempChangeDetected = true;
      }
    }
  }

  uint32_t unixTimestamp = 0;
  char dateString[11];
  char timeString[9];
  bool timeChangeDetected = false;
  if (currentMillis - previousMillisRTC >= RTC_SAMPLE_RATE_DELAY_MS) {
    previousMillisRTC = currentMillis;
    timeChangeDetected = true;
    if constexpr (ENABLE_RTC) {
      setTCAChannel(MULTIPLEXER_TCA9548A_I2C_CHANNEL_TIME);
      DateTime now = rtc.now();
      unixTimestamp = now.unixtime();
      snprintf(dateString, sizeof(dateString), "%04d-%02d-%02d",
               now.year(), now.month(), now.day());
      snprintf(timeString, sizeof(timeString), "%02d:%02d:%02d",
               now.hour(), now.minute(), now.second());
    } else {
      snprintf(dateString, sizeof(dateString), "2024-12-01");
      snprintf(timeString, sizeof(timeString), "12:00:01");
    }
  }

  // detect change in temperature/humidity
  if constexpr (ENABLE_LCD) {
    if (tempChangeDetected || timeChangeDetected) {
      char tempString[LCD_COLS];
      setTCAChannel(MULTIPLEXER_TCA9548A_I2C_CHANNEL_LCD);
      sprintf(tempString, "%d C ", previousTemperature);
      lcd.setCursor(2, 0);
      lcd.print(tempString);
      sprintf(tempString, "%d H ", previousHumidity);
      lcd.setCursor(2, 1);
      lcd.print(tempString);
    }
    if (timeChangeDetected) {
      setTCAChannel(MULTIPLEXER_TCA9548A_I2C_CHANNEL_LCD);
      lcd.setCursor(2, 2);
      lcd.print(dateString);
      lcd.setCursor(2, 3);
      lcd.print(timeString);
    }
  }

  if (tempChangeDetected) {
    Serial.print(dateString);
    Serial.print(" ");
    Serial.print(timeString);
    Serial.print(" - ");
    Serial.print(previousTemperature);
    Serial.print(" *C, ");
    Serial.print(previousHumidity);
    Serial.println(" H");
  }

  if constexpr (ENABLE_SD_CARD_LOGGING) {
    // TODO: This crashes the arduino
    #if ENABLE_SD_CARD
    if (sdOn && tempChangeDetected) {
      // init SD Card
      if (!sdInitalized && !SD.begin(PIN_SD_CARD_SELECT_LOGS)) {
        digitalWrite(PIN_LED_ERROR, HIGH);
        Serial.println("ERROR: SD Card initialization unsuccessful (make sure the card is formatted as single partition FAT32)");
      }
      sdInitalized = true;
      if (sdInitalized && !SD.exists(FILENAME_SD_CARD_LOGS_CSV)) {
        Serial.println("Initalize SD Card...");
        File dataFile = SD.open(FILENAME_SD_CARD_LOGS_CSV, FILE_WRITE);
        if (dataFile) {
          dataFile.println(CSV_HEADER_SD_CARD_LOGS_CSV);
          dataFile.close();
        } else {
          digitalWrite(PIN_LED_ERROR, HIGH);
          Serial.print("ERROR: Could not initalize/write/create/open ");
          Serial.println(FILENAME_SD_CARD_LOGS_CSV);
          sdInitalized = false;
        }
      }
      if (sdInitalized) {
        File dataFile = SD.open(FILENAME_SD_CARD_LOGS_CSV, FILE_READ);
        if (dataFile) {
          unsigned long fileSize = dataFile.size();
          dataFile.close();
          Serial.print("Found existing log file ");
          Serial.print(FILENAME_SD_CARD_LOGS_CSV);
          Serial.print(" (size=");
          Serial.print(fileSize);
          Serial.println("byte)");
        } else {
          Serial.print("Found no existing log file ");
          Serial.print(FILENAME_SD_CARD_LOGS_CSV);
          sdInitalized = false;
        }
      }
      if (sdInitalized) {
        File dataFile = SD.open(FILENAME_SD_CARD_LOGS_CSV, O_APPEND);
        // if the file is available, write to it:
        if (dataFile) {
          dataFile.print(unixTimestamp);
          dataFile.print(",");
          dataFile.print(previousTemperature);
          dataFile.print(",");
          dataFile.println(previousHumidity);
          unsigned long fileSize = dataFile.size();
          Serial.print("Wrote to existing log file ");
          Serial.print(FILENAME_SD_CARD_LOGS_CSV);
          Serial.print(" (size=");
          Serial.print(fileSize);
          Serial.println("byte)");
        }
        // if the file isn't open, pop up an error:
        else {
          digitalWrite(PIN_LED_ERROR, HIGH);
          Serial.print("ERROR: Could not write/open ");
          Serial.println(FILENAME_SD_CARD_LOGS_CSV);
          sdInitalized = false;
        }
      }
    }
    #endif
  }

  delay(LOOP_DELAY);
}
