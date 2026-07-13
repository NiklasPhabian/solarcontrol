# Waveshare ESP32-S3 Relay 1CH — Modbus RTU Bridge

Single-channel relay module based on the ESP32-S3, controlled exclusively via
Modbus RTU over RS485. No WiFi, BLE, or RTC features are used.

## Modbus register map

| Function code | Address | Value | Description |
|---|---|---|---|
| FC 05 – Write Single Coil | `0x0000` | `0xFF00` | Relay ON |
| FC 05 – Write Single Coil | `0x0000` | `0x0000` | Relay OFF |
| FC 01 – Read Coil Status | `0x0000` | qty 1 | Returns `1` (ON) or `0` (OFF) |
| FC 03 – Read Holding Registers | `0x0000` | qty 1 | Returns `1` (ON) or `0` (OFF) |

**Slave ID:** 7 (hardcoded — change `SLAVE_ID` in the bridge code to reassign)  
**Serial:** 9600 baud, 8N1

## Pin map

| GPIO | Function |
|---|---|
| 47 | Relay CH1 coil driver |
| 17 | RS485 TX (UART1) |
| 18 | RS485 RX (UART1) |
| 21 | RS485 DE/RE (auto-managed by ESP32 UART hardware) |
| 2 | Activity LED — pulses 50 ms on every valid addressed frame |

## Bridge code

Flash to the ESP32-S3 via Arduino IDE (board: **ESP32S3 Dev Module**) or
`arduino-cli` with FQBN `esp32:esp32:esp32s3`.

```cpp
// MODBUS_RELAY.ino
//
// Modbus RTU slave for the Waveshare ESP32-S3-Relay-1CH.
// Controls the onboard relay exclusively via RS485 — no WiFi, BLE, or RTC.
//
// Slave ID : 7  (change SLAVE_ID below if needed)
// Baud rate: 9600, 8N1
//
// Supported Modbus commands:
//   FC 05  Write Single Coil  coil address 0x0000
//       0xFF00 → relay ON
//       0x0000 → relay OFF
//   FC 01  Read Coil Status   coil address 0x0000, quantity 1
//       Returns current relay state (bit 0 of byte: 0x00 or 0x01)
//   FC 03  Read Holding Registers  register address 0x0000, quantity 1
//       Returns relay state as 16-bit word: 0x0001 (ON) or 0x0000 (OFF)
//
// Pin map:
//   GPIO 47  Relay CH1 coil driver
//   GPIO 17  RS485 TX  (UART1)
//   GPIO 18  RS485 RX  (UART1)
//   GPIO 21  RS485 DE/RE — auto-managed by the ESP32 UART hardware
//   GPIO  2  Activity LED  ← verify this against your board schematic;
//                            change LED_PIN if it does not match

#include <HardwareSerial.h>

/***********************************************************  Config  ***********************************************************/
#define SLAVE_ID   7
#define BAUD_RATE  9600

/***********************************************************  Pins  *************************************************************/
#define GPIO_PIN_CH1  47
#define TXD1          17
#define RXD1          18
#define TXD1EN        21
#define LED_PIN        2   // <── change if your board uses a different GPIO

/***********************************************************  Modbus  ***********************************************************/
#define FC_READ_COILS              0x01
#define FC_READ_HOLDING_REGISTERS  0x03
#define FC_WRITE_SINGLE_COIL       0x05
#define EX_ILLEGAL_FUNCTION   0x01
#define EX_ILLEGAL_ADDRESS    0x02
#define EX_ILLEGAL_VALUE      0x03

// Inter-frame silent gap: 3.5 char times @ 9600 baud ≈ 3.65 ms
#define FRAME_TIMEOUT_MS  5

HardwareSerial rs485Serial(1);

bool     relayState = false;
uint32_t ledOffMs   = 0;

/*************************************************************  Relay  **********************************************************/
void Relay_Open(void)  { digitalWrite(GPIO_PIN_CH1, HIGH); relayState = true;  printf("|***  Relay CH1 on  ***|\r\n"); }
void Relay_Closs(void) { digitalWrite(GPIO_PIN_CH1, LOW);  relayState = false; printf("|***  Relay CH1 off ***|\r\n"); }

/***********************************************************  CRC-16  ***********************************************************/
// Standard Modbus CRC-16/IBM — result bytes transmitted LSB first
uint16_t crc16(const uint8_t *buf, uint8_t len) {
  uint16_t crc = 0xFFFF;
  for (uint8_t i = 0; i < len; i++) {
    crc ^= buf[i];
    for (uint8_t j = 0; j < 8; j++)
      crc = (crc & 1) ? (crc >> 1) ^ 0xA001 : (crc >> 1);
  }
  return crc;
}

/***********************************************************  RS485  ************************************************************/
// Append CRC and send; flush() holds until all bytes shift out so DE releases cleanly
void sendFrame(uint8_t *frame, uint8_t len) {
  uint16_t crc   = crc16(frame, len);
  frame[len]     = crc & 0xFF;
  frame[len + 1] = crc >> 8;
  rs485Serial.write(frame, len + 2);
  rs485Serial.flush();
}

void sendException(uint8_t fc, uint8_t code) {
  uint8_t resp[5] = { SLAVE_ID, (uint8_t)(fc | 0x80), code };
  sendFrame(resp, 3);
}

/***********************************************************  Modbus frame handler  *********************************************/
void processFrame(const uint8_t *buf, uint8_t len) {
  if (len < 8) return;

  uint16_t rxCrc = buf[len - 2] | ((uint16_t)buf[len - 1] << 8);
  if (crc16(buf, len - 2) != rxCrc) {
    printf("RS485 Data : CRC error – frame discarded\r\n");
    return;
  }

  if (buf[0] != SLAVE_ID) return;   // Not addressed to us – no response

  // Flash activity LED on every valid addressed frame
  digitalWrite(LED_PIN, HIGH);
  ledOffMs = millis() + 50;

  uint8_t  fc   = buf[1];
  uint16_t addr = ((uint16_t)buf[2] << 8) | buf[3];
  uint16_t val  = ((uint16_t)buf[4] << 8) | buf[5];

  printf("RS485 Data : FC=0x%02X addr=0x%04X val=0x%04X\r\n", fc, addr, val);

  if (fc == FC_WRITE_SINGLE_COIL) {
    if (addr != 0x0000)     { sendException(fc, EX_ILLEGAL_ADDRESS); return; }
    if      (val == 0xFF00)   Relay_Open();
    else if (val == 0x0000)   Relay_Closs();
    else                    { sendException(fc, EX_ILLEGAL_VALUE);   return; }

    // FC05 response echoes the first 6 bytes of the request
    uint8_t resp[8];
    memcpy(resp, buf, 6);
    sendFrame(resp, 6);

  } else if (fc == FC_READ_COILS) {
    if (addr != 0x0000 || val != 1) { sendException(fc, EX_ILLEGAL_ADDRESS); return; }
    uint8_t resp[6] = { SLAVE_ID, fc, 0x01, relayState ? 0x01 : 0x00 };
    sendFrame(resp, 4);

  } else if (fc == FC_READ_HOLDING_REGISTERS) {
    if (addr != 0x0000 || val != 1) { sendException(fc, EX_ILLEGAL_ADDRESS); return; }
    // Register 0: relay state as 16-bit value (0x0000 off, 0x0001 on)
    uint8_t resp[7] = { SLAVE_ID, fc, 0x02, 0x00, relayState ? 0x01 : 0x00 };
    sendFrame(resp, 5);

  } else {
    sendException(fc, EX_ILLEGAL_FUNCTION);
  }
}

/***********************************************************  Frame accumulator  ************************************************/
uint8_t  rxBuf[32];
uint8_t  rxLen     = 0;
uint32_t lastByteMs = 0;

/***********************************************************  Initializing  *****************************************************/
void setup() {
  pinMode(GPIO_PIN_CH1, OUTPUT);
  pinMode(LED_PIN,       OUTPUT);
  digitalWrite(GPIO_PIN_CH1, LOW);
  digitalWrite(LED_PIN,       LOW);

  rs485Serial.begin(BAUD_RATE, SERIAL_8N1, RXD1, TXD1);
  if (!rs485Serial.setPins(-1, -1, -1, TXD1EN))
    printf("Failed to set TXDEN pins\r\n");
  if (!rs485Serial.setMode(UART_MODE_RS485_HALF_DUPLEX))
    printf("Failed to set RS485 mode\r\n");

  printf("Modbus RTU slave ready  ID=%d  %d 8N1\r\n", SLAVE_ID, BAUD_RATE);
}

/***********************************************************  While  ************************************************************/
void loop() {
  while (rs485Serial.available()) {
    if (rxLen < sizeof(rxBuf))
      rxBuf[rxLen++] = rs485Serial.read();
    else
      rxLen = 0;    // Buffer overrun – discard and re-sync
    lastByteMs = millis();
  }

  // Silent gap after the last byte signals end-of-frame
  if (rxLen > 0 && millis() - lastByteMs >= FRAME_TIMEOUT_MS) {
    processFrame(rxBuf, rxLen);
    rxLen = 0;
  }

  // Non-blocking LED off
  if (ledOffMs && millis() >= ledOffMs) {
    digitalWrite(LED_PIN, LOW);
    ledOffMs = 0;
  }
}
```
