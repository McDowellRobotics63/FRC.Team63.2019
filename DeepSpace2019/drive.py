
import math

import wpilib
from wpilib import SmartDashboard

import ctre
import robotmap
from robotenums import DriveState

from ctre.pigeonimu import PigeonIMU
from ctre.pigeonimu import PigeonIMU_StatusFrame

import pathfinder as pf

class DeepSpaceDrive():
  USING_MOTION_ARC = False

  def __init__(self, logger):
    self.logger = logger
    self.simulation = False

  def init(self):
    self.logger.info("DeepSpaceDrive::init()")
    self.timer = wpilib.Timer()
    self.timer.start()

    self.current_state = DriveState.OPERATOR_CONTROL

    self.pigeon = PigeonIMU(robotmap.PIGEON_IMU_CAN_ID)

    self.leftTalonMaster = ctre.WPI_TalonSRX(robotmap.DRIVE_LEFT_MASTER_CAN_ID)
    self.leftTalonSlave = ctre.WPI_TalonSRX(robotmap.DRIVE_LEFT_SLAVE_CAN_ID)

    self.rightTalonMaster = ctre.WPI_TalonSRX(robotmap.DRIVE_RIGHT_MASTER_CAN_ID)
    self.rightTalonSlave = ctre.WPI_TalonSRX(robotmap.DRIVE_RIGHT_SLAVE_CAN_ID)

    self.dummyTalon = ctre.TalonSRX(robotmap.CLAW_LEFT_WHEELS_CAN_ID)

    self.talons = [self.leftTalonMaster, self.leftTalonSlave, self.rightTalonMaster, self.rightTalonSlave]
    self.masterTalons = [self.leftTalonMaster, self.rightTalonMaster]

    self.drive = wpilib.RobotDrive(self.leftTalonMaster, self.rightTalonMaster)
    self.drive.setSafetyEnabled(False)

    self.drive_front_extend = wpilib.Solenoid(robotmap.PCM1_CANID, robotmap.DRIVE_FRONT_EXTEND_SOLENOID)
    self.drive_front_retract = wpilib.Solenoid(robotmap.PCM1_CANID, robotmap.DRIVE_FRONT_RETRACT_SOLENOID)
    self.drive_back_extend = wpilib.Solenoid(robotmap.PCM1_CANID, robotmap.DRIVE_REAR_EXTEND_SOLENOID)
    self.drive_back_retract = wpilib.Solenoid(robotmap.PCM1_CANID, robotmap.DRIVE_REAR_RETRACT_SOLENOID)

  def config(self, simulation):
    self.simulation = simulation
    self.logger.info("DeepSpaceDrive::config()")

    if not simulation:
      self.dummyTalon.configRemoteFeedbackFilter(self.leftTalonSlave.getDeviceID(), ctre.RemoteSensorSource.TalonSRX_SelectedSensor, 0, robotmap.CAN_TIMEOUT_MS)
      self.dummyTalon.configRemoteFeedbackFilter(self.rightTalonSlave.getDeviceID(), ctre.RemoteSensorSource.TalonSRX_SelectedSensor, 1, robotmap.CAN_TIMEOUT_MS)
    self.dummyTalon.configSensorTerm(0, ctre.FeedbackDevice.RemoteSensor0, robotmap.CAN_TIMEOUT_MS)
    self.dummyTalon.configSensorTerm(1, ctre.FeedbackDevice.RemoteSensor1, robotmap.CAN_TIMEOUT_MS)
    self.dummyTalon.configSelectedFeedbackSensor(ctre.FeedbackDevice.SensorSum, 0, robotmap.CAN_TIMEOUT_MS)   
    self.dummyTalon.configSelectedFeedbackCoefficient(1.0, 0, robotmap.CAN_TIMEOUT_MS)
    self.dummyTalon.setStatusFramePeriod(ctre._impl.StatusFrame.Status_2_Feedback0, 10, robotmap.CAN_TIMEOUT_MS)

    '''Configuration items common for all talons'''
    for talon in self.talons:
      talon.configNominalOutputForward(0.0, robotmap.CAN_TIMEOUT_MS)
      talon.configNominalOutputReverse(0.0, robotmap.CAN_TIMEOUT_MS)
      talon.configPeakOutputForward(1.0, robotmap.CAN_TIMEOUT_MS)
      talon.configPeakOutputReverse(-1.0, robotmap.CAN_TIMEOUT_MS)
      talon.enableVoltageCompensation(True)
      talon.configVoltageCompSaturation(11.5, robotmap.CAN_TIMEOUT_MS)
      talon.configOpenLoopRamp(0.125, robotmap.CAN_TIMEOUT_MS)

    self.leftTalonMaster.setInverted(False)
    self.leftTalonSlave.setInverted(False)
    self.rightTalonMaster.setInverted(True)
    self.rightTalonSlave.setInverted(True)

    self.leftTalonSlave.configSelectedFeedbackSensor(ctre.FeedbackDevice.QuadEncoder, 0, robotmap.CAN_TIMEOUT_MS)
    self.leftTalonSlave.configSelectedFeedbackCoefficient(1.0, 0, robotmap.CAN_TIMEOUT_MS)
    self.leftTalonSlave.setSensorPhase(True)
    self.leftTalonSlave.setStatusFramePeriod(ctre._impl.StatusFrame.Status_2_Feedback0, 10, robotmap.CAN_TIMEOUT_MS)
    self.leftTalonSlave.set(ctre.ControlMode.Follower, robotmap.DRIVE_LEFT_MASTER_CAN_ID)    

    self.rightTalonSlave.configSelectedFeedbackSensor(ctre.FeedbackDevice.QuadEncoder, 0, robotmap.CAN_TIMEOUT_MS)
    self.rightTalonSlave.configSelectedFeedbackCoefficient(1.0, 0, robotmap.CAN_TIMEOUT_MS)
    self.rightTalonSlave.setSensorPhase(True)
    self.rightTalonSlave.setStatusFramePeriod(ctre._impl.StatusFrame.Status_2_Feedback0, 10, robotmap.CAN_TIMEOUT_MS)
    self.rightTalonSlave.set(ctre.ControlMode.Follower, robotmap.DRIVE_RIGHT_MASTER_CAN_ID)

    if self.USING_MOTION_ARC:
      self.leftTalonMaster.configRemoteFeedbackFilter(self.dummyTalon.getDeviceID(), ctre.RemoteSensorSource.TalonSRX_SelectedSensor, 0, robotmap.CAN_TIMEOUT_MS)
    else:
      if not simulation:
        self.leftTalonMaster.configRemoteFeedbackFilter(self.leftTalonSlave.getDeviceID(), ctre.RemoteSensorSource.TalonSRX_SelectedSensor, 0, robotmap.CAN_TIMEOUT_MS)
        self.leftTalonMaster.configRemoteFeedbackFilter(robotmap.PIGEON_IMU_CAN_ID, ctre.RemoteSensorSource.Pigeon_Yaw, 1, robotmap.CAN_TIMEOUT_MS)

    if self.USING_MOTION_ARC:
      self.rightTalonMaster.configRemoteFeedbackFilter(self.dummyTalon.getDeviceID(), ctre.RemoteSensorSource.TalonSRX_SelectedSensor, 0, robotmap.CAN_TIMEOUT_MS)
    else:
      if not simulation:
        self.rightTalonMaster.configRemoteFeedbackFilter(self.rightTalonSlave.getDeviceID(), ctre.RemoteSensorSource.TalonSRX_SelectedSensor, 0, robotmap.CAN_TIMEOUT_MS)
        self.rightTalonMaster.configRemoteFeedbackFilter(robotmap.PIGEON_IMU_CAN_ID, ctre.RemoteSensorSource.Pigeon_Yaw, 1, robotmap.CAN_TIMEOUT_MS)

    for talon in self.masterTalons:
      if not simulation:
        talon.configMotionProfileTrajectoryPeriod(robotmap.BASE_TRAJECTORY_PERIOD_MS)

      talon.config_kP(0, 0.375, robotmap.CAN_TIMEOUT_MS)
      talon.config_kI(0, 0.0, robotmap.CAN_TIMEOUT_MS)
      talon.config_kD(0, 0.0, robotmap.CAN_TIMEOUT_MS)
      talon.config_kF(0, 0.35, robotmap.CAN_TIMEOUT_MS)

      talon.config_kP(1, 7.0, robotmap.CAN_TIMEOUT_MS)
      talon.config_kI(1, 0.0, robotmap.CAN_TIMEOUT_MS)
      talon.config_kD(1, 8.0, robotmap.CAN_TIMEOUT_MS)
      talon.config_kF(1, 0.0, robotmap.CAN_TIMEOUT_MS)

      talon.selectProfileSlot(0, 0)
      talon.configClosedLoopPeakOutput(0, 1.0, robotmap.CAN_TIMEOUT_MS)

      talon.selectProfileSlot(1, 1)
      talon.configClosedLoopPeakOutput(1, 1.0, robotmap.CAN_TIMEOUT_MS)

      talon.configSelectedFeedbackSensor(ctre.FeedbackDevice.RemoteSensor0, 0, robotmap.CAN_TIMEOUT_MS)
      talon.configSelectedFeedbackSensor(ctre.FeedbackDevice.RemoteSensor1, 1, robotmap.CAN_TIMEOUT_MS)
      talon.configSelectedFeedbackCoefficient(1.0, 0, robotmap.CAN_TIMEOUT_MS)
      talon.configSelectedFeedbackCoefficient(3600 / robotmap.PIGEON_UNITS_PER_ROTATION, 1, robotmap.CAN_TIMEOUT_MS)

    self.drive_front_extend.set(False)
    self.drive_front_retract.set(True)
    self.drive_back_extend.set(False)
    self.drive_back_retract.set(True)

  def drive_straight(self, value):
    self.drive.arcadeDrive(value, 0, False)

  def iterate(self, robot_mode, pilot_stick, copilot_stick):
    pilot_x = pilot_stick.LeftStickX()
    pilot_y = pilot_stick.LeftStickY()

    if abs(pilot_x) > 0 or abs(pilot_y) > 0:
      self.current_state = DriveState.OPERATOR_CONTROL
      self.drive.arcadeDrive(pilot_x, pilot_y, False)
    else:
      if self.current_state == DriveState.FOLLOW_PATH:
        self.process_auto_path()

    if pilot_stick.X().get():
      self.drive_front_extend.set(True)
      self.drive_front_retract.set(False)
      self.drive_back_extend.set(False)
      self.drive_back_retract.set(True)
    elif pilot_stick.Y().get():
      self.drive_front_extend.set(False)
      self.drive_front_retract.set(True)
      self.drive_back_extend.set(True)
      self.drive_back_retract.set(False)
    elif pilot_stick.B().get():
      self.drive_front_extend.set(False)
      self.drive_front_retract.set(True)
      self.drive_back_extend.set(False)
      self.drive_back_retract.set(True)

    SmartDashboard.putString("Drive State", self.current_state.name)

  def disable(self):
    self.logger.info("DeepSpaceDrive::disable()")
  
  def follow_a_path(self, trajectory):
    self.pigeon.setYaw(0, robotmap.CAN_TIMEOUT_MS)
    self.pigeon.setFusedHeading(0, robotmap.CAN_TIMEOUT_MS)

    self.leftTalonSlave.setSelectedSensorPosition(0, 0, robotmap.CAN_TIMEOUT_MS)
    self.leftTalonSlave.getSensorCollection().setQuadraturePosition(0, robotmap.CAN_TIMEOUT_MS)
    if not self.simulation:
      self.leftTalonMaster.clearMotionProfileTrajectories()
      self.leftTalonMaster.clearMotionProfileHasUnderrun(0)
    if self.USING_MOTION_ARC:
      self.leftTalonMaster.set(ctre.ControlMode.MotionProfileArc, 0)
    else:
      self.leftTalonMaster.set(ctre.ControlMode.MotionProfile, 0)

    self.rightTalonSlave.setSelectedSensorPosition(0, 0, robotmap.CAN_TIMEOUT_MS)
    self.rightTalonSlave.getSensorCollection().setQuadraturePosition(0, robotmap.CAN_TIMEOUT_MS)
    if not self.simulation:
      self.rightTalonMaster.clearMotionProfileTrajectories()
      self.rightTalonMaster.clearMotionProfileHasUnderrun(0)
    if self.USING_MOTION_ARC:
      self.rightTalonMaster.set(ctre.ControlMode.MotionProfileArc, 0)
    else:
      self.rightTalonMaster.set(ctre.ControlMode.MotionProfile, 0)

    modifier = pf.modifiers.TankModifier(trajectory).modify(2.1) #Wheelbase in feet

    self.leftTrajectory = modifier.getLeftTrajectory()
    self.rightTrajectory = modifier.getRightTrajectory()

    for i in range(len(trajectory)):
      leftSeg = self.leftTrajectory[i]
      rightSeg = self.rightTrajectory[i]

      if self.USING_MOTION_ARC:
        lposition = self.inchesToUnits((leftSeg.position + rightSeg.position) * 12)
        rposition = self.inchesToUnits((leftSeg.position + rightSeg.position) * 12)
      else:
        lposition = self.inchesToUnits((leftSeg.position) * 12)
        rposition = self.inchesToUnits((rightSeg.position) * 12)
      
      if self.USING_MOTION_ARC:
        aux_position = 10 * math.degrees(leftSeg.heading)
      else:
        aux_position = 0

      if self.USING_MOTION_ARC:
        aux_velocity = 0 #What should this be?
      else:
        aux_velocity = 0
      
      slot0 = 0
      slot1 = 1
      timeDur = 0
      zeroPos = bool(i == 0)
      isLastPoint = bool(i == len(trajectory) - 1)
      lvelocity = self.inchesToUnits(leftSeg.velocity * 12) / 10
      rvelocity = self.inchesToUnits(rightSeg.velocity * 12) / 10

      larbitrary_feed_forward = 0
      rarbitrary_feed_forward = 0
      aux_feed_forward = 0

      self.leftTrajectory[i] = ctre.BTrajectoryPoint(lposition, lvelocity, larbitrary_feed_forward, aux_position, aux_velocity, aux_feed_forward, slot0, slot1, isLastPoint, zeroPos, timeDur, self.USING_MOTION_ARC)
      self.rightTrajectory[i] = ctre.BTrajectoryPoint(rposition, rvelocity, rarbitrary_feed_forward, aux_position, aux_velocity, aux_feed_forward, slot0, slot1, isLastPoint, zeroPos, timeDur, self.USING_MOTION_ARC)

    for point in self.leftTrajectory:
      if not self.simulation:
        self.leftTalonMaster.pushMotionProfileTrajectory(point)

    for point in self.rightTrajectory:
      if not self.simulation:
        self.rightTalonMaster.pushMotionProfileTrajectory(point)

    self.leftDone = False
    self.rightDone = False
    self.motionProfileEnabled = False
    self.bufferProcessingStartTime = 0
    self.executionStartTime = 0
    self.executionFinishTime = 0

    self.current_state = DriveState.FOLLOW_PATH

  def process_auto_path(self):
    if self.simulation:
      self.leftDone = True
      self.rightDone = True
    else:
      self.leftMPStatus = self.leftTalonMaster.getMotionProfileStatus()
      self.rightMPStatus = self.rightTalonMaster.getMotionProfileStatus()

      '''
      The processMotionProfileBuffer() moves trajectory points from the
      "Top" level buffer into the "Bottom" level buffer.  This just means
      they are moved from a buffer inside the roboRIO into a buffer inside
      the Talon firmware itself.  The more sophisticated method is to call
      this function on a seperate background thread which is running at a rate which
      is twice as fast as the duration of the trajectory points.  Then in the main thread
      check that the bottom buffer count is high enough to trigger the motion
      profile execution to begin.  That allows the motion profile execution to
      begin sooner.  For this test we can just wait until the top buffer has
      been completely (mostly) emptied into the bottom buffer.
      '''

      '''Let's time this to see if it's really worth doing it the more sophisticated way'''
      if not self.motionProfileEnabled and self.leftMPStatus.btmBufferCnt == 0 and self.rightMPStatus.btmBufferCnt == 0:
        self.logger.info("Beginning to funnel trajectory points into the Talons")
        self.bufferProcessingStartTime = self.timer.getFPGATimestamp()

      '''
      Don't print anything while funneling points into the Talons.
      Printing will slow down execution and we want to measure time
      that it took to do this operation.
      '''
      if self.leftMPStatus.topBufferCnt > 0 and self.leftMPStatus.btmBufferCnt < 50:
        self.leftTalonMaster.processMotionProfileBuffer()

      if self.rightMPStatus.topBufferCnt > 0 and self.rightMPStatus.btmBufferCnt < 50:
        self.rightTalonMaster.processMotionProfileBuffer()

      if not self.motionProfileEnabled and \
        self.leftMPStatus.btmBufferCnt > 20 and \
        self.rightMPStatus.btmBufferCnt > 20:
        if self.USING_MOTION_ARC:
          self.leftTalonMaster.set(ctre.ControlMode.MotionProfileArc, 1)
          self.rightTalonMaster.set(ctre.ControlMode.MotionProfileArc, 1)
        else:
          self.leftTalonMaster.set(ctre.ControlMode.MotionProfile, 1)
          self.rightTalonMaster.set(ctre.ControlMode.MotionProfile, 1)
        self.motionProfileEnabled = True
        self.executionStartTime = self.timer.getFPGATimestamp()
        self.logger.info("Beginning motion profile execution")

      if self.leftMPStatus.isLast and self.leftMPStatus.outputEnable == ctre.SetValueMotionProfile.Enable and not self.leftDone:
        self.leftTalonMaster.neutralOutput()
        self.leftTalonMaster.set(ctre.ControlMode.PercentOutput, 0)
        self.leftDone = True
        self.logger.info("Left motion profile is finished executing")

      if self.rightMPStatus.isLast and self.rightMPStatus.outputEnable == ctre.SetValueMotionProfile.Enable and not self.rightDone:
        self.rightTalonMaster.neutralOutput()
        self.rightTalonMaster.set(ctre.ControlMode.PercentOutput, 0)
        self.rightDone = True
        self.logger.info("Right motion profile is finished executing")

    if self.leftDone and self.rightDone:
      self.executionFinishTime = self.timer.getFPGATimestamp()
      self.current_state = DriveState.OPERATOR_CONTROL

  def unitsToInches(self, units):
    return units * robotmap.WHEEL_CIRCUMFERENCE / robotmap.DRIVE_ENCODER_COUNTS_PER_REV

  def inchesToUnits(self, inches):
    return inches * robotmap.DRIVE_ENCODER_COUNTS_PER_REV / robotmap.WHEEL_CIRCUMFERENCE
