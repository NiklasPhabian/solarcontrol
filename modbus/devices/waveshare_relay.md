# Bride code:

```cpp
#include <ModbusRTUSlave.h>
#include <Preferences.h> // 1. Added for permanent memory [1]

#define RX_PIN    15   
#define TX_PIN    16   
#define EN_PIN    4    
#define RELAY_PIN 47   
#define LED_PIN   1    

// 2. This is now just a fallback if memory is empty
const uint8_t DEFAULT_SLAVE_ID = 7; 

ModbusRTUSlave modbus(Serial2, EN_PIN);
Preferences pref; // 3. Added permanent memory object

bool coil = {false}; 
uint16_t holdingRegs = {7}; // 4. Added Holding Register 0 to hold the Slave ID

void setup() {
  pinMode(RELAY_PIN, OUTPUT);
  pinMode(LED_PIN, OUTPUT);
  
  digitalWrite(RELAY_PIN, LOW);
  digitalWrite(LED_PIN, LOW); 

  // 5. Load the saved Slave ID from memory (use 7 if empty) [1]
  pref.begin("modbus_cfg", false);
  holdingRegs = pref.getUInt("slave_id", DEFAULT_SLAVE_ID); 

  // 6. Map BOTH the coil and the holding register to Modbus
  modbus.configureCoils(coil, 1);
  modbus.configureHoldingRegisters(holdingRegs, 1); 
  
  Serial2.begin(9600, SERIAL_8N1, RX_PIN, TX_PIN);
  
  // 7. Start Modbus using the dynamically loaded address
  modbus.begin(holdingRegs);
}

void loop() {
  // 8. Capture the ID before checking for new messages
  uint16_t oldID = holdingRegs;

  if (modbus.poll()) {
    digitalWrite(LED_PIN, HIGH);
    delay(50); 
    digitalWrite(LED_PIN, LOW);

    // 9. If a Modbus command just changed Holding Register 0, save it!
    if (holdingRegs != oldID) {
      // Ensure the new ID is valid for Modbus (1 to 247)
      if (holdingRegs >= 1 && holdingRegs <= 247) {
        pref.putUInt("slave_id", holdingRegs); // Save to flash [1]
        modbus.begin(holdingRegs);             // Apply new address immediately
      } else {
        holdingRegs = oldID; // Revert if master sent an invalid address
      }
    }
  }
  
  digitalWrite(RELAY_PIN, coil ? HIGH : LOW);
}
```