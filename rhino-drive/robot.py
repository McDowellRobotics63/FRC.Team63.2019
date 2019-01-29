#!/usr/bin/env python3
"""
    This is a demo program showing the use of the RobotDrive class,
    specifically it contains the code necessary to operate a robot with
    tank drive.
"""

import wpilib
from wpilib.drive import DifferentialDrive


class MyRobot(wpilib.IterativeRobot):
    def robotInit(self):
        """Robot initialization function"""

        # object that handles basic drive operations
        self.leftMotor = wpilib.Talon(1)
        self.rightMotor = wpilib.Talon(2)

        self.frontSolExtend = wpilib.Solenoid(1, 1)
        self.frontSolRetract = wpilib.Solenoid(1, 0)
        self.rearSolExtend = wpilib.Solenoid(1, 3)
        self.rearSolRetract = wpilib.Solenoid(1, 2)

        self.frontSolExtend.set(False)
        self.frontSolRetract.set(True)
        self.rearSolExtend.set(False)
        self.rearSolRetract.set(True)
        
        self.myRobot = DifferentialDrive(self.leftMotor, self.rightMotor)
        self.myRobot.setExpiration(0.1)

        # joysticks 1 & 2 on the driver station
        self.stick = wpilib.Joystick(0)

    def disabled(self):
        """Called when the robot is disabled"""
        self.leftMotor.set(0)
        self.rightMotor.set(0)
        while self.isDisabled():
            wpilib.Timer.delay(0.01)

    def teleopInit(self):
        """Executed at the start of teleop mode"""
        self.myRobot.setSafetyEnabled(True)

    def teleopPeriodic(self):
        """Runs the motors with tank steering"""
        self.myRobot.tankDrive(self.stick.getRawAxis(5), self.stick.getRawAxis(1))

        if self.stick.getRawButtonPressed(1): #A
            self.frontSolExtend.set(False)
            self.frontSolRetract.set(True)
        elif self.stick.getRawButtonPressed(4): #Y
            self.frontSolExtend.set(True)
            self.frontSolRetract.set(False)
        elif self.stick.getRawButtonPressed(2): #B
            self.rearSolExtend.set(True)
            self.rearSolRetract.set(False)
        elif self.stick.getRawButtonPressed(3): #X
            self.rearSolExtend.set(False)
            self.rearSolRetract.set(True)

if __name__ == "__main__":
    wpilib.run(MyRobot)
