// Declare the current RGB animation state
enum LEDAnimationState
{
  RED_TO_GREEN,
  GREEN_TO_BLUE,
  BLUE_TO_RED
};

constexpr int LED_PIN_BLUE = 3;
constexpr int LED_PIN_GREEN = 5;
constexpr int LED_PIN_RED = 6;

constexpr int BUTTON_ON = 9;
constexpr int BUTTON_OFF = 8;

constexpr int POWER_SAVE_DELAY_MS = 1;
constexpr int COLOR_CHANGE_INTERVAL_MS = POWER_SAVE_DELAY_MS * 4;
constexpr int BUTTON_DEBOUNCE_DELAY_MS = 200;

// Global variables
// > LEDs ON/OFF
bool ledOn;
// > RGB LED values
uint8_t redValue;
uint8_t greenValue;
uint8_t blueValue;
// > Animation to perform
LEDAnimationState ledAnimationState;
// > Timestamp for color changes
unsigned long lastColorChangeTime = 0;

// Function to get the current color (uses variable references)
void getCurrentColor(uint8_t& red, uint8_t& green, uint8_t& blue, LEDAnimationState& state)
{
  switch (state)
  {
  case LEDAnimationState::RED_TO_GREEN:
    if (red > 0)
    {
      red--;
      green++;
    }
    else
    {
      state = LEDAnimationState::GREEN_TO_BLUE;
    }
    break;
  case LEDAnimationState::GREEN_TO_BLUE:
    if (green > 0)
    {
      green--;
      blue++;
    }
    else
    {
      state = LEDAnimationState::BLUE_TO_RED;
    }
    break;
  case LEDAnimationState::BLUE_TO_RED:
    if (blue > 0)
    {
      blue--;
      red++;
    }
    else
    {
      state = LEDAnimationState::RED_TO_GREEN;
    }
    break;
  }
}

void setup()
{
  // initialize digital pins for the RED, GREEN and BLUE LED as an output
  pinMode(LED_PIN_RED, OUTPUT);
  pinMode(LED_PIN_GREEN, OUTPUT);
  pinMode(LED_PIN_BLUE, OUTPUT);

  // initialize digital pins for the on and off button
  pinMode(BUTTON_ON, INPUT_PULLUP);
  pinMode(BUTTON_OFF, INPUT_PULLUP);

  // initialize global variables
  ledOn = true;

  redValue = 255;
  greenValue = 0;
  blueValue = 0;

  ledAnimationState = LEDAnimationState::RED_TO_GREEN;
}

void loop()
{
  if (digitalRead(BUTTON_ON) == LOW)
  {
    ledOn = true;
    delay(BUTTON_DEBOUNCE_DELAY_MS);
  }
  if (digitalRead(BUTTON_OFF) == LOW)
  {
    ledOn = false;
    delay(BUTTON_DEBOUNCE_DELAY_MS);
  }

  if (ledOn)
  {
    unsigned long currentMillis = millis();
    if (currentMillis - lastColorChangeTime >= COLOR_CHANGE_INTERVAL_MS)
    {
      lastColorChangeTime = currentMillis;

      getCurrentColor(redValue, greenValue, blueValue, ledAnimationState);

      analogWrite(LED_PIN_RED, redValue);
      analogWrite(LED_PIN_GREEN, greenValue);
      analogWrite(LED_PIN_BLUE, blueValue);
    }
  }
  else
  {
    analogWrite(LED_PIN_RED, 0);
    analogWrite(LED_PIN_GREEN, 0);
    analogWrite(LED_PIN_BLUE, 0);
  }

  delay(POWER_SAVE_DELAY_MS);
}
