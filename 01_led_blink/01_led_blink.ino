/*
  Blink

  Turns an LED on and off repeatedly using the given delay in ms.

  Most Arduinos have an on-board LED you can control.
  On the UNO R3 it can be found on the digital pin 13.
  LED_BUILTIN is set to the correct LED pin independent of which board is used.

  This code is based on the public domain example:
  https://www.arduino.cc/en/Tutorial/BuiltInExamples/Blink
*/

constexpr int DELAY_MS = 3 * 1000;

// the setup function runs once when you press reset or power the board
void setup()
{
  // initialize digital pin LED_BUILTIN as an output
  // => the pin can now send voltage signals (either HIGH or LOW) to any
  //    component connected to it, such as an LED
  pinMode(LED_BUILTIN, OUTPUT);
  // by default all pins are set to input on Arduino startup, which means
  // they are high-impedance and do not source or sink current

  // setup the serial output
  // => the argument is the baud rate (the speed of communication, measured in bits per second (bps))
  //    9600 bits per second is a standard speed for serial communication
  Serial.begin(9600);
  Serial.println("LED_BUILTIN is the pin " + String(LED_BUILTIN));
}

// the loop function runs over and over again forever
void loop()
{
  // make the voltage level HIGH on the digital pin 13/LED
  // => turns the board and a connected LED on
  digitalWrite(LED_BUILTIN, HIGH);
  Serial.println("LED ON");
  // do nothing else for the time of the delay
  delay(DELAY_MS);

  // make the voltage level LOW on the digital  pin 13/LED
  // => turns the board and a connected LED off
  digitalWrite(LED_BUILTIN, LOW);
  Serial.println("LED OFF");
  // do nothing else for the time of the delay
  delay(DELAY_MS);
}
