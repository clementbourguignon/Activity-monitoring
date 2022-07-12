// change number of PIR sensors and first pin here:
const int n_pirs = 12;
const int first_pin = 0;

int PIR_chan[n_pirs];
int PIR[n_pirs];

void setup() {
  Serial.begin(115200);
  // Set all channels to pullup inputs
  for (int i = 0; i < n_pirs; i++) {
    PIR_chan[i] = i + first_pin;
    pinmode(PIR_chan[i], INPUT_PULLUP);
  }
}

void loop() {
  // Print n-1 first chans with tab
  for (int i = 0; i < n_pirs-1; i++) {
    Serial.print(String(digitalRead(PIR_chan[i])) + '\t');
  }
  // Print last chan with carriage return
  Serial.print(String(digitalRead(PIR_chan[n_pirs-1])) + '\n');

  // set sampling period, 4 Hz is more than enough
  delay(250);
}
