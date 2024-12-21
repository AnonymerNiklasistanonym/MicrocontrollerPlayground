def i2c_scan(i2c, logger=print):
    devices = i2c.scan()
    if devices:
        logger("I2C devices found at addresses:")
        for device in devices:
            logger(hex(device))
    else:
        raise RuntimeError("No I2C devices found!")
