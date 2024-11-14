constexpr int LED_RED = 5;
constexpr int BUTTON_ON = 9;
constexpr int BUTTON_OFF = 8;

constexpr int LOOP_DELAY_MS = 10;
constexpr int BUTTON_DEBOUNCE_DELAY_MS = 200;

void setup()
{
  pinMode(LED_RED, OUTPUT);
  pinMode(BUTTON_ON, INPUT_PULLUP);
  pinMode(BUTTON_OFF, INPUT_PULLUP);
}

void loop()
{
  if (digitalRead(BUTTON_ON) == LOW)
  {
    digitalWrite(LED_RED, HIGH);
    delay(BUTTON_DEBOUNCE_DELAY_MS);
  }
  if (digitalRead(BUTTON_OFF) == LOW)
  {
    digitalWrite(LED_RED, LOW);
    delay(BUTTON_DEBOUNCE_DELAY_MS);
  }
  // limit the amount of times the loop is executed
  // => reduce unnecessary processor load and power draw
  delay(LOOP_DELAY_MS);
}
