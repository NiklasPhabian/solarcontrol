"""FHS280 heat pump controller Modbus device abstraction."""

from __future__ import annotations

from typing import Optional

from .base import ModbusDevice

from ..transport import ModbusController


class FHS280(ModbusDevice):
    """FHS280 heat-pump controller (Modbus RTU) abstraction."""

    # Holding Registers (4x)
    REG_SETPOINT = 4
    REG_T_MIN = 5
    REG_T2_MIN = 6
    REG_TIMER = 7  # 0=Off, 1=On
    REG_START_HP_HOUR = 8
    REG_START_HP_MIN = 9
    REG_STOP_HP_HOUR = 10
    REG_STOP_HP_MIN = 11
    REG_HP_PUMP = 12  # 0=Off, 1=Only HP, 2=Only EL, 3=HP+EL, 4=Boiler, 5=HP+Boiler
    REG_LEGIONEL_AUTO_FUNCTION = 13  # 0=Off, 1=60°C, 2=65°C
    REG_WWPROTEC = 14
    REG_FAN_OPER = 15  # AC: 0=Low, 1=High | EC: 0=Off, 1=Low, 2=Mid, 3=High
    REG_FAN_CON = 16  # 0=Off, 1=EC Low, 2=EC Mid, 3=EC High
    REG_SOLACEL = 17  # 0=Off, 1=Only HP, 2=Only EL, 3=HP+EL
    REG_SC_HP = 18
    REG_SC_EL = 19
    REG_HOLIDAY = 20  # 0=Off, 1=1 Week, 2=2 Weeks, 3=3 Weeks, 4=3 Days, 5=Manual
    REG_MAN_DAYS_SET = 21
    REG_BOOST = 22
    REG_FAN_PAUSE = 23  # 0=Off, 1=30m/15s, 2=30m/30s, 3=60m/15s, 4=60m/30s, 5=90m/15s, 6=90m/30s
    REG_LANGUAGE = 25  # 0=English, 1=German, 2=French, 3=Dutch, 4=Spanish, 5=Italian, 6=Danish, 7=Swedish, 8=Norwegian, 9=Polish, 10=Slovenian, 11=Croatian
    REG_DEFROST = 26  # 0=Air, 1=Gas, 2=Tmin RF
    REG_ANODE = 27
    REG_T_MAX = 28
    REG_FAN_TYPE = 29  # 0=AC, 1=EC
    REG_EC_FAN_LEVEL1 = 30
    REG_EC_FAN_LEVEL2 = 31
    REG_EC_FAN_LEVEL3 = 32
    REG_LEGIONEL_AUTO_FUNCTION_DAYS = 33
    REG_RTC_SEC = 103
    REG_RTC_MIN = 104
    REG_RTC_HOUR = 105
    REG_RTC_DAY = 106
    REG_RTC_DATE = 107
    REG_RTC_MONTH = 108
    REG_RTC_YEAR = 109
    REG_MODBUS_ADDRESS = 114
    REG_MODBUS_BAUDRATE = 115  # 1=19200, 2=9600
    REG_MODBUS_PARITY = 116  # 0=None, 1=Odd, 2=Even
    REG_MODBUS_ALLOW_WRITE = 117  # 1=Allow write

    # Input Registers (3x)
    REG_INPUT_DI1_PRESSOSTAT = 0
    REG_INPUT_DI2_SOLAR = 1
    REG_INPUT_T1 = 7  # Evaporator Temperature
    REG_INPUT_T2 = 8  # Tank Temperature
    REG_INPUT_RELAY1_COMPRESSOR = 9
    REG_INPUT_RELAY2_ELPATRON = 10
    REG_INPUT_RELAY3_KEDEL = 11
    REG_INPUT_RELAY4_MAGNETVALVE = 12
    REG_INPUT_RELAY6_KONDENSATOR = 13
    REG_INPUT_RELAY7_VENTILATOR = 14
    REG_INPUT_DA0_0_10V = 15  # EC fan only
    REG_INPUT_STATUS = 16
    REG_INPUT_REST_DAYS = 17
    REG_INPUT_UNIT_ALARM = 18
    REG_INPUT_T3 = 19
    REG_INPUT_FW_VERSION = 119

    # State mappings for registers with meaningful state values
    TIMER_STATES = {0: "Off", 1: "On"}
    HP_PUMP_STATES = {0: "Off", 1: "Only HP", 2: "Only EL", 3: "HP+EL", 4: "Boiler", 5: "HP+Boiler"}
    LEGIONEL_AUTO_FUNCTION_STATES = {0: "Off", 1: "60°C", 2: "65°C"}
    SOLACEL_STATES = {0: "Off", 1: "Only HP", 2: "Only EL", 3: "HP+EL"}
    HOLIDAY_STATES = {0: "Off", 1: "1 Week", 2: "2 Weeks", 3: "3 Weeks", 4: "3 Days", 5: "Manual"}
    FAN_PAUSE_STATES = {0: "Off", 1: "30m/15s", 2: "30m/30s", 3: "60m/15s", 4: "60m/30s", 5: "90m/15s", 6: "90m/30s"}
    LANGUAGE_STATES = {0: "English", 1: "German", 2: "French", 3: "Dutch", 4: "Spanish", 5: "Italian", 6: "Danish", 7: "Swedish", 8: "Norwegian", 9: "Polish", 10: "Slovenian", 11: "Croatian"}
    DEFROST_STATES = {0: "Air", 1: "Gas", 2: "Tmin RF"}
    FAN_TYPE_STATES = {0: "AC", 1: "EC"}
    MODBUS_BAUDRATE_STATES = {1: "19200", 2: "9600"}
    MODBUS_PARITY_STATES = {0: "None", 1: "Odd", 2: "Even"}
    FAN_OPER_AC_STATES = {0: "Low", 1: "High"}
    FAN_OPER_EC_STATES = {0: "Off", 1: "Low", 2: "Mid", 3: "High"}
    FAN_CON_STATES = {0: "Off", 1: "EC Low", 2: "EC Mid", 3: "EC High"}

    def __init__(self, controller, slave_address: int = 1) -> None:
        super().__init__(controller, slave_address)

    def read_holding_value(self, address: int, *, count: int = 1) -> list[int]:
        return self.read_holding_registers(address, count)

    def write_holding_value(self, address: int, value: int) -> None:
        self.write_register(address, int(value))

    def read_setpoint(self) -> int:
        return self.read_uint16(self.REG_SETPOINT)

    def write_setpoint(self, value: int) -> None:
        self.write_holding_value(self.REG_SETPOINT, value)

    def read_t_min(self) -> int:
        return self.read_uint16(self.REG_T_MIN)

    def write_t_min(self, value: int) -> None:
        self.write_holding_value(self.REG_T_MIN, value)

    def read_t2_min(self) -> int:
        return self.read_uint16(self.REG_T2_MIN)

    def write_t2_min(self, value: int) -> None:
        self.write_holding_value(self.REG_T2_MIN, value)

    def read_timer(self) -> int:
        return self.read_uint16(self.REG_TIMER)

    def read_timer_state(self) -> str:
        value = self.read_timer()
        return self.TIMER_STATES.get(value, f"Unknown({value})")

    def write_timer(self, value: int) -> None:
        self.write_holding_value(self.REG_TIMER, value)

    def read_start_hp_hour(self) -> int:
        return self.read_uint16(self.REG_START_HP_HOUR)

    def write_start_hp_hour(self, value: int) -> None:
        self.write_holding_value(self.REG_START_HP_HOUR, value)

    def read_start_hp_min(self) -> int:
        return self.read_uint16(self.REG_START_HP_MIN)

    def write_start_hp_min(self, value: int) -> None:
        self.write_holding_value(self.REG_START_HP_MIN, value)

    def read_stop_hp_hour(self) -> int:
        return self.read_uint16(self.REG_STOP_HP_HOUR)

    def write_stop_hp_hour(self, value: int) -> None:
        self.write_holding_value(self.REG_STOP_HP_HOUR, value)

    def read_stop_hp_min(self) -> int:
        return self.read_uint16(self.REG_STOP_HP_MIN)

    def write_stop_hp_min(self, value: int) -> None:
        self.write_holding_value(self.REG_STOP_HP_MIN, value)

    def read_hp_pump(self) -> int:
        return self.read_uint16(self.REG_HP_PUMP)

    def read_hp_pump_state(self) -> str:
        value = self.read_hp_pump()
        return self.HP_PUMP_STATES.get(value, f"Unknown({value})")

    def write_hp_pump(self, value: int) -> None:
        self.write_holding_value(self.REG_HP_PUMP, value)

    def read_legionel_auto_function(self) -> int:
        return self.read_uint16(self.REG_LEGIONEL_AUTO_FUNCTION)

    def read_legionel_auto_function_state(self) -> str:
        value = self.read_legionel_auto_function()
        return self.LEGIONEL_AUTO_FUNCTION_STATES.get(value, f"Unknown({value})")

    def write_legionel_auto_function(self, value: int) -> None:
        self.write_holding_value(self.REG_LEGIONEL_AUTO_FUNCTION, value)

    def read_wwprotec(self) -> int:
        return self.read_uint16(self.REG_WWPROTEC)

    def write_wwprotec(self, value: int) -> None:
        self.write_holding_value(self.REG_WWPROTEC, value)

    def read_fan_oper(self) -> int:
        return self.read_uint16(self.REG_FAN_OPER)

    def read_fan_oper_state(self) -> str:
        """Fan operation mode. AC: 0=Low, 1=High | EC: 0=Off, 1=Low, 2=Mid, 3=High"""
        value = self.read_fan_oper()
        fan_type = self.read_fan_type()
        if fan_type == 0:  # AC
            return self.FAN_OPER_AC_STATES.get(value, f"Unknown({value})")
        else:  # EC
            return self.FAN_OPER_EC_STATES.get(value, f"Unknown({value})")

    def write_fan_oper(self, value: int) -> None:
        self.write_holding_value(self.REG_FAN_OPER, value)

    def read_fan_con(self) -> int:
        return self.read_uint16(self.REG_FAN_CON)

    def read_fan_con_state(self) -> str:
        """Fan control mode: 0=Off, 1=EC Low, 2=EC Mid, 3=EC High"""
        value = self.read_fan_con()
        return self.FAN_CON_STATES.get(value, f"Unknown({value})")

    def write_fan_con(self, value: int) -> None:
        self.write_holding_value(self.REG_FAN_CON, value)

    def read_solacel(self) -> int:
        return self.read_uint16(self.REG_SOLACEL)

    def read_solacel_state(self) -> str:
        """PV solar charging mode: 0=Off, 1=Only HP, 2=Only EL, 3=HP+EL"""
        value = self.read_solacel()
        return self.SOLACEL_STATES.get(value, f"Unknown({value})")

    def write_solacel(self, value: int) -> None:
        self.write_holding_value(self.REG_SOLACEL, value)

    def set_solacel_off(self) -> None:
        """Disable PV solar charging."""
        self.write_solacel(0)

    def set_solacel_only_hp(self) -> None:
        """Enable PV solar charging for heat pump only."""
        self.write_solacel(1)

    def set_solacel_only_el(self) -> None:
        """Enable PV solar charging for electric heater only."""
        self.write_solacel(2)

    def set_solacel_hp_and_el(self) -> None:
        """Enable PV solar charging for both heat pump and electric heater."""
        self.write_solacel(3)

    def read_sc_hp(self) -> int:
        return self.read_uint16(self.REG_SC_HP)

    def write_sc_hp(self, value: int) -> None:
        self.write_holding_value(self.REG_SC_HP, value)

    def read_sc_el(self) -> int:
        return self.read_uint16(self.REG_SC_EL)

    def write_sc_el(self, value: int) -> None:
        self.write_holding_value(self.REG_SC_EL, value)

    def read_holiday(self) -> int:
        return self.read_uint16(self.REG_HOLIDAY)

    def read_holiday_state(self) -> str:
        value = self.read_holiday()
        return self.HOLIDAY_STATES.get(value, f"Unknown({value})")

    def write_holiday(self, value: int) -> None:
        self.write_holding_value(self.REG_HOLIDAY, value)

    def read_man_days_set(self) -> int:
        return self.read_uint16(self.REG_MAN_DAYS_SET)

    def write_man_days_set(self, value: int) -> None:
        self.write_holding_value(self.REG_MAN_DAYS_SET, value)

    def read_boost(self) -> int:
        return self.read_uint16(self.REG_BOOST)

    def write_boost(self, value: int) -> None:
        self.write_holding_value(self.REG_BOOST, value)

    def read_fan_pause(self) -> int:
        return self.read_uint16(self.REG_FAN_PAUSE)

    def read_fan_pause_state(self) -> str:
        value = self.read_fan_pause()
        return self.FAN_PAUSE_STATES.get(value, f"Unknown({value})")

    def write_fan_pause(self, value: int) -> None:
        self.write_holding_value(self.REG_FAN_PAUSE, value)

    def read_language(self) -> int:
        return self.read_uint16(self.REG_LANGUAGE)

    def read_language_state(self) -> str:
        value = self.read_language()
        return self.LANGUAGE_STATES.get(value, f"Unknown({value})")

    def write_language(self, value: int) -> None:
        self.write_holding_value(self.REG_LANGUAGE, value)

    def read_defrost(self) -> int:
        return self.read_uint16(self.REG_DEFROST)

    def read_defrost_state(self) -> str:
        value = self.read_defrost()
        return self.DEFROST_STATES.get(value, f"Unknown({value})")

    def write_defrost(self, value: int) -> None:
        self.write_holding_value(self.REG_DEFROST, value)

    def read_anode(self) -> int:
        return self.read_uint16(self.REG_ANODE)

    def write_anode(self, value: int) -> None:
        self.write_holding_value(self.REG_ANODE, value)

    def read_t_max(self) -> int:
        return self.read_uint16(self.REG_T_MAX)

    def write_t_max(self, value: int) -> None:
        self.write_holding_value(self.REG_T_MAX, value)

    def read_fan_type(self) -> int:
        return self.read_uint16(self.REG_FAN_TYPE)

    def read_fan_type_state(self) -> str:
        value = self.read_fan_type()
        return self.FAN_TYPE_STATES.get(value, f"Unknown({value})")

    def write_fan_type(self, value: int) -> None:
        self.write_holding_value(self.REG_FAN_TYPE, value)

    def read_ec_fan_level1(self) -> int:
        return self.read_uint16(self.REG_EC_FAN_LEVEL1)

    def write_ec_fan_level1(self, value: int) -> None:
        self.write_holding_value(self.REG_EC_FAN_LEVEL1, value)

    def read_ec_fan_level2(self) -> int:
        return self.read_uint16(self.REG_EC_FAN_LEVEL2)

    def write_ec_fan_level2(self, value: int) -> None:
        self.write_holding_value(self.REG_EC_FAN_LEVEL2, value)

    def read_ec_fan_level3(self) -> int:
        return self.read_uint16(self.REG_EC_FAN_LEVEL3)

    def write_ec_fan_level3(self, value: int) -> None:
        self.write_holding_value(self.REG_EC_FAN_LEVEL3, value)

    def read_legionel_auto_function_days(self) -> int:
        return self.read_uint16(self.REG_LEGIONEL_AUTO_FUNCTION_DAYS)

    def write_legionel_auto_function_days(self, value: int) -> None:
        self.write_holding_value(self.REG_LEGIONEL_AUTO_FUNCTION_DAYS, value)

    def read_rtc_sec(self) -> int:
        return self.read_uint16(self.REG_RTC_SEC)

    def write_rtc_sec(self, value: int) -> None:
        self.write_holding_value(self.REG_RTC_SEC, value)

    def read_rtc_min(self) -> int:
        return self.read_uint16(self.REG_RTC_MIN)

    def write_rtc_min(self, value: int) -> None:
        self.write_holding_value(self.REG_RTC_MIN, value)

    def read_rtc_hour(self) -> int:
        return self.read_uint16(self.REG_RTC_HOUR)

    def write_rtc_hour(self, value: int) -> None:
        self.write_holding_value(self.REG_RTC_HOUR, value)

    def read_rtc_day(self) -> int:
        return self.read_uint16(self.REG_RTC_DAY)

    def write_rtc_day(self, value: int) -> None:
        self.write_holding_value(self.REG_RTC_DAY, value)

    def read_rtc_date(self) -> int:
        return self.read_uint16(self.REG_RTC_DATE)

    def write_rtc_date(self, value: int) -> None:
        self.write_holding_value(self.REG_RTC_DATE, value)

    def read_rtc_month(self) -> int:
        return self.read_uint16(self.REG_RTC_MONTH)

    def write_rtc_month(self, value: int) -> None:
        self.write_holding_value(self.REG_RTC_MONTH, value)

    def read_rtc_year(self) -> int:
        return self.read_uint16(self.REG_RTC_YEAR)

    def write_rtc_year(self, value: int) -> None:
        self.write_holding_value(self.REG_RTC_YEAR, value)

    def read_modbus_address(self) -> int:
        return self.read_uint16(self.REG_MODBUS_ADDRESS)

    def write_modbus_address(self, value: int) -> None:
        self.write_holding_value(self.REG_MODBUS_ADDRESS, value)

    def read_modbus_baudrate(self) -> int:
        return self.read_uint16(self.REG_MODBUS_BAUDRATE)

    def read_modbus_baudrate_state(self) -> str:
        value = self.read_modbus_baudrate()
        return self.MODBUS_BAUDRATE_STATES.get(value, f"Unknown({value})")

    def write_modbus_baudrate(self, value: int) -> None:
        self.write_holding_value(self.REG_MODBUS_BAUDRATE, value)

    def read_modbus_parity(self) -> int:
        return self.read_uint16(self.REG_MODBUS_PARITY)

    def read_modbus_parity_state(self) -> str:
        value = self.read_modbus_parity()
        return self.MODBUS_PARITY_STATES.get(value, f"Unknown({value})")

    def write_modbus_parity(self, value: int) -> None:
        self.write_holding_value(self.REG_MODBUS_PARITY, value)

    def read_modbus_allow_write(self) -> int:
        return self.read_uint16(self.REG_MODBUS_ALLOW_WRITE)

    def write_modbus_allow_write(self, value: int) -> None:
        self.write_holding_value(self.REG_MODBUS_ALLOW_WRITE, value)

    def read_di1_pressostat(self) -> int:
        return self.read_uint16(self.REG_INPUT_DI1_PRESSOSTAT, input_registers=True)

    def read_di2_solar(self) -> int:
        return self.read_uint16(self.REG_INPUT_DI2_SOLAR, input_registers=True)

    def read_t1(self) -> float:
        return self.read_int16(self.REG_INPUT_T1, input_registers=True) / 10.0

    def read_t2(self) -> float:
        return self.read_int16(self.REG_INPUT_T2, input_registers=True) / 10.0

    def read_relay1_kompressor(self) -> bool:
        return bool(int(self.read_uint16(self.REG_INPUT_RELAY1_COMPRESSOR, input_registers=True)))

    def read_relay2_elpatron(self) -> bool:
        return bool(int(self.read_uint16(self.REG_INPUT_RELAY2_ELPATRON, input_registers=True)))

    def read_relay3_kedel(self) -> int:
        return self.read_uint16(self.REG_INPUT_RELAY3_KEDEL, input_registers=True)

    def read_relay4_magnetventil(self) -> int:
        return self.read_uint16(self.REG_INPUT_RELAY4_MAGNETVALVE, input_registers=True)

    def read_relay6_kondensator(self) -> int:
        return self.read_uint16(self.REG_INPUT_RELAY6_KONDENSATOR, input_registers=True)

    def read_relay7_ventilator(self) -> int:
        return self.read_uint16(self.REG_INPUT_RELAY7_VENTILATOR, input_registers=True)

    def read_da0_0_10v(self) -> int:
        return self.read_uint16(self.REG_INPUT_DA0_0_10V, input_registers=True)

    def read_status(self) -> int:
        return self.read_uint16(self.REG_INPUT_STATUS, input_registers=True)

    def read_rest_days(self) -> int:
        return self.read_uint16(self.REG_INPUT_REST_DAYS, input_registers=True)

    def read_unit_alarm(self) -> int:
        return self.read_uint16(self.REG_INPUT_UNIT_ALARM, input_registers=True)

    def read_t3(self) -> float:
        return self.read_int16(self.REG_INPUT_T3, input_registers=True) / 10.0

    def read_fw_version(self) -> float:
        return self.read_uint16(self.REG_INPUT_FW_VERSION, input_registers=True) / 10.0

    def read_all_holding_registers(self) -> dict[str, int]:
        return {
            "setpoint": self.read_setpoint(),
            "t_min": self.read_t_min(),
            "t2_min": self.read_t2_min(),
            "timer": self.read_timer(),
            "start_hp_hour": self.read_start_hp_hour(),
            "start_hp_min": self.read_start_hp_min(),
            "stop_hp_hour": self.read_stop_hp_hour(),
            "stop_hp_min": self.read_stop_hp_min(),
            "hp_pump": self.read_hp_pump(),
            "legionel_auto_function": self.read_legionel_auto_function(),
            "wwprotec": self.read_wwprotec(),
            "fan_oper": self.read_fan_oper(),
            "fan_con": self.read_fan_con(),
            "solacel": self.read_solacel(),
            "sc_hp": self.read_sc_hp(),
            "sc_el": self.read_sc_el(),
            "holiday": self.read_holiday(),
            "man_days_set": self.read_man_days_set(),
            "boost": self.read_boost(),
            "fan_pause": self.read_fan_pause(),
            "language": self.read_language(),
            "defrost": self.read_defrost(),
            "anode": self.read_anode(),
            "t_max": self.read_t_max(),
            "fan_type": self.read_fan_type(),
            "ec_fan_level1": self.read_ec_fan_level1(),
            "ec_fan_level2": self.read_ec_fan_level2(),
            "ec_fan_level3": self.read_ec_fan_level3(),
            "legionel_auto_function_days": self.read_legionel_auto_function_days(),
            "rtc_sec": self.read_rtc_sec(),
            "rtc_min": self.read_rtc_min(),
            "rtc_hour": self.read_rtc_hour(),
            "rtc_day": self.read_rtc_day(),
            "rtc_date": self.read_rtc_date(),
            "rtc_month": self.read_rtc_month(),
            "rtc_year": self.read_rtc_year(),
            "modbus_address": self.read_modbus_address(),
            "modbus_baudrate": self.read_modbus_baudrate(),
            "modbus_parity": self.read_modbus_parity(),
            "modbus_allow_write": self.read_modbus_allow_write(),
        }
    
    def read_all_input_registers(self) -> dict[str, int | float]:
        return {
            "di1_pressostat": self.read_di1_pressostat(),
            "di2_solar": self.read_di2_solar(),
            "t1": self.read_t1(),
            "t2": self.read_t2(),
            "relay1_kompressor": self.read_relay1_kompressor(),
            "relay2_elpatron": self.read_relay2_elpatron(),
            "relay3_kedel": self.read_relay3_kedel(),
            "relay4_magnetventil": self.read_relay4_magnetventil(),
            "relay6_kondensator": self.read_relay6_kondensator(),
            "relay7_ventilator": self.read_relay7_ventilator(),
            "da0_0_10v": self.read_da0_0_10v(),
            "status": self.read_status(),
            "rest_days": self.read_rest_days(),
            "unit_alarm": self.read_unit_alarm(),
            "t3": self.read_t3(),
            "fw_version": self.read_fw_version(),
        }


__all__ = ["FHS280"]


def main():    
    port = '/dev/ttyUSB0'
    slave_address = 6
    controller = ModbusController(port=port)
    controller.connect()
    try:
        fhs280 = FHS280(controller, slave_address)
        fhs280_data = fhs280.read_all_input_registers()
        for reg, value in fhs280_data.items():
            print(f"{reg}: {value}")       
    finally:
        controller.close()


def solacell():
    port = '/dev/ttyUSB0'
    slave_address = 6
    controller = ModbusController(port=port)
    controller.connect()
    try:
        fhs280 = FHS280(controller, slave_address)
        print(fhs280.read_solacel())
    finally:
        controller.close()


if __name__ == "__main__":
    solacell()