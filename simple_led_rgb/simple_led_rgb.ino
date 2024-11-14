constexpr int LED_PIN_BLUE = 3;
constexpr int LED_PIN_GREEN = 5;
constexpr int LED_PIN_RED = 6;

constexpr int DELAY_MS = 4;

void setup() {
  // initialize digital pins for the RED, GREEN and BLUE LED as an output
  // => the pin can now send voltage signals (either HIGH or LOW)
  pinMode(LED_PIN_RED, OUTPUT);
  pinMode(LED_PIN_GREEN, OUTPUT);
  pinMode(LED_PIN_BLUE, OUTPUT);

  // setup the serial output
  Serial.begin(9600);
  Serial.println(String("LED_PIN_RED is the pin ") + LED_PIN_RED);
  Serial.println(String("LED_PIN_GREEN is the pin ") + LED_PIN_GREEN);
  Serial.println(String("LED_PIN_BLUE is the pin ") + LED_PIN_BLUE);
}

// Initial color RED
uint8_t redValue = 255;
uint8_t greenValue = 0;
uint8_t blueValue = 0;

void loop() {
  // red -> green
  for (uint8_t i = 0; i < 255; i++)
  {
    analogWrite(LED_PIN_RED, --redValue);
    analogWrite(LED_PIN_GREEN, ++greenValue);
    analogWrite(LED_PIN_BLUE, blueValue);
    delay(DELAY_MS);
  }
  Serial.println("GREEN (" + String(redValue) + ","  + String(greenValue) + ","  + String(blueValue) + ")");

  // green -> blue
  for (uint8_t i = 0; i < 255; i++)
  {
    analogWrite(LED_PIN_RED, redValue);
    analogWrite(LED_PIN_GREEN, --greenValue);
    analogWrite(LED_PIN_BLUE, ++blueValue);
    delay(DELAY_MS);
  }
  Serial.println("BLUE (" + String(redValue) + ","  + String(greenValue) + ","  + String(blueValue) + ")");

  // blue -> red
  for (uint8_t i = 0; i < 255; i++)
  {
    analogWrite(LED_PIN_RED, ++redValue);
    analogWrite(LED_PIN_GREEN, greenValue);
    analogWrite(LED_PIN_BLUE, --blueValue);
    delay(DELAY_MS);
  }
  Serial.println("RED (" + String(redValue) + ","  + String(greenValue) + ","  + String(blueValue) + ")");
}
