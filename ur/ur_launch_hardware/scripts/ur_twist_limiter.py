#!/usr/bin/env python3

import rospy

from geometry_msgs.msg import Twist


class UR_twist_limiter():
    
    def config(self):
        self.input_command_topic = rospy.get_param("~input_command_topic", "/cmd_vel")
        self.output_command_topic = rospy.get_param("~output_command_topic", "/cmd_vel_limited")
        
        self.lin_vel_limit = rospy.get_param("~lin_vel_limit", 0.1)
        self.angular_vel_limit = rospy.get_param("~angular_vel_limit", 0.1)
        self.lin_acc_limit = rospy.get_param("~lin_acc_limit", 0.1)
        self.angular_acc_limit = rospy.get_param("~angular_acc_limit", 0.1)
        self.lin_jerk_limit = rospy.get_param("~lin_jerk_limit", 0.01)
        self.angular_jerk_limit = rospy.get_param("~angular_jerk_limit", 0.1)
        self.command_timeout = rospy.get_param("~command_timeout", 0.5)
    
    def __init__(self):
        rospy.init_node("ur_twist_limiter")
        self.config()
        
        rospy.Subscriber(self.input_command_topic, Twist, self.input_callback)
        self.output_pub = rospy.Publisher(self.output_command_topic, Twist, queue_size=1)
        
        self.initial_run = True
        
    def monitor(self):
        self.last_command_timestamp = rospy.Time.now()
        while not rospy.is_shutdown():
            if self.last_command_timestamp + rospy.Duration(self.command_timeout) < rospy.Time.now():
                self.output_pub.publish(Twist())
            rospy.sleep(0.1)
        

    def input_callback(self,msg = Twist()):
        now = rospy.Time.now()
        self.last_command_timestamp = now
        
        vel_scale_factor = 1.0
        
        # limit velocity
        if abs(msg.linear.x) > self.lin_vel_limit:
            vel_scale_factor = self.lin_vel_limit / abs(msg.linear.x)
        if abs(msg.linear.y) > self.lin_vel_limit and abs(msg.linear.y) * vel_scale_factor > self.lin_vel_limit:
            vel_scale_factor = self.lin_vel_limit / abs(msg.linear.y)
        if abs(msg.linear.z) > self.lin_vel_limit and abs(msg.linear.z) * vel_scale_factor > self.lin_vel_limit:
            vel_scale_factor = self.lin_vel_limit / abs(msg.linear.z)
        if abs(msg.angular.x) > self.angular_vel_limit and abs(msg.angular.x) * vel_scale_factor > self.angular_vel_limit:
            vel_scale_factor = self.angular_vel_limit / abs(msg.angular.x)
        if abs(msg.angular.y) > self.angular_vel_limit and abs(msg.angular.y) * vel_scale_factor > self.angular_vel_limit:
            vel_scale_factor = self.angular_vel_limit / abs(msg.angular.y)
        if abs(msg.angular.z) > self.angular_vel_limit and abs(msg.angular.z) * vel_scale_factor > self.angular_vel_limit:
            vel_scale_factor = self.angular_vel_limit / abs(msg.angular.z)
            
        # apply velocity limit
        msg = self.apply_vel_scale_factor(msg, vel_scale_factor)
        vel_scale_factor = 1.0 # reset scale factor
        
        # on intial run set time old
        if self.initial_run:
            self.last_command = Twist()
            self.time_old = rospy.Time.now()
            self.last_acc = Twist()
            self.initial_run = False
            return
        
        # limit acceleration
        dt = (now - self.time_old).to_sec()
        
        if abs(msg.linear.x - self.last_command.linear.x) / dt > self.lin_acc_limit:
            msg.linear.x = self.last_command.linear.x + self.lin_acc_limit * dt * (msg.linear.x - self.last_command.linear.x) / abs(msg.linear.x - self.last_command.linear.x)
        if abs(msg.linear.y - self.last_command.linear.y) / dt > self.lin_acc_limit and abs(msg.linear.y - self.last_command.linear.y) / dt * vel_scale_factor > self.lin_acc_limit:
            msg.linear.y = self.last_command.linear.y + self.lin_acc_limit * dt * (msg.linear.y - self.last_command.linear.y) / abs(msg.linear.y - self.last_command.linear.y)
        if abs(msg.linear.z - self.last_command.linear.z) / dt > self.lin_acc_limit and abs(msg.linear.z - self.last_command.linear.z) / dt * vel_scale_factor > self.lin_acc_limit:
            msg.linear.z = self.last_command.linear.z + self.lin_acc_limit * dt * (msg.linear.z - self.last_command.linear.z) / abs(msg.linear.z - self.last_command.linear.z)
        if abs(msg.angular.x - self.last_command.angular.x) / dt > self.angular_acc_limit and abs(msg.angular.x - self.last_command.angular.x) / dt * vel_scale_factor > self.angular_acc_limit:
            msg.angular.x = self.last_command.angular.x + self.angular_acc_limit * dt * (msg.angular.x - self.last_command.angular.x) / abs(msg.angular.x - self.last_command.angular.x)
        if abs(msg.angular.y - self.last_command.angular.y) / dt > self.angular_acc_limit and abs(msg.angular.y - self.last_command.angular.y) / dt * vel_scale_factor > self.angular_acc_limit:
            msg.angular.y = self.last_command.angular.y + self.angular_acc_limit * dt * (msg.angular.y - self.last_command.angular.y) / abs(msg.angular.y - self.last_command.angular.y)
        if abs(msg.angular.z - self.last_command.angular.z) / dt > self.angular_acc_limit and abs(msg.angular.z - self.last_command.angular.z) / dt * vel_scale_factor > self.angular_acc_limit:
            msg.angular.z = self.last_command.angular.z + self.angular_acc_limit * dt * (msg.angular.z - self.last_command.angular.z) / abs(msg.angular.z - self.last_command.angular.z)
        
        # apply velocity limit
        # msg = self.apply_vel_scale_factor(msg, vel_scale_factor)
        # vel_scale_factor = 1.0 # reset scale factor
        
        # limit jerk
        if abs(msg.linear.x - self.last_command.linear.x) / dt - self.last_acc.linear.x / dt > self.lin_jerk_limit:
            msg.linear.x = self.last_command.linear.x + self.lin_jerk_limit * dt * (msg.linear.x - self.last_command.linear.x) / abs(msg.linear.x - self.last_command.linear.x) + self.last_acc.linear.x / dt * dt
        if abs(msg.linear.y - self.last_command.linear.y) / dt - self.last_acc.linear.y / dt > self.lin_jerk_limit and abs(msg.linear.y - self.last_command.linear.y) / dt - self.last_acc.linear.y / dt * vel_scale_factor > self.lin_jerk_limit:
            msg.linear.y = self.last_command.linear.y + self.lin_jerk_limit * dt * (msg.linear.y - self.last_command.linear.y) / abs(msg.linear.y - self.last_command.linear.y) + self.last_acc.linear.y / dt * dt
        if abs(msg.linear.z - self.last_command.linear.z) / dt - self.last_acc.linear.z / dt > self.lin_jerk_limit and abs(msg.linear.z - self.last_command.linear.z) / dt - self.last_acc.linear.z / dt * vel_scale_factor > self.lin_jerk_limit:
            msg.linear.z = self.last_command.linear.z + self.lin_jerk_limit * dt * (msg.linear.z - self.last_command.linear.z) / abs(msg.linear.z - self.last_command.linear.z) + self.last_acc.linear.z / dt * dt
        if abs(msg.angular.x - self.last_command.angular.x) / dt - self.last_acc.angular.x / dt > self.angular_jerk_limit and abs(msg.angular.x - self.last_command.angular.x) / dt - self.last_acc.angular.x / dt * vel_scale_factor > self.angular_jerk_limit:
            msg.angular.x = self.last_command.angular.x + self.angular_jerk_limit * dt * (msg.angular.x - self.last_command.angular.x) / abs(msg.angular.x - self.last_command.angular.x) + self.last_acc.angular.x / dt * dt
        if abs(msg.angular.y - self.last_command.angular.y) / dt - self.last_acc.angular.y / dt > self.angular_jerk_limit and abs(msg.angular.y - self.last_command.angular.y) / dt - self.last_acc.angular.y / dt * vel_scale_factor > self.angular_jerk_limit:
            msg.angular.y = self.last_command.angular.y + self.angular_jerk_limit * dt * (msg.angular.y - self.last_command.angular.y) / abs(msg.angular.y - self.last_command.angular.y) + self.last_acc.angular.y / dt * dt
        if abs(msg.angular.z - self.last_command.angular.z) / dt - self.last_acc.angular.z / dt > self.angular_jerk_limit and abs(msg.angular.z - self.last_command.angular.z) / dt - self.last_acc.angular.z / dt * vel_scale_factor > self.angular_jerk_limit:
            msg.angular.z = self.last_command.angular.z + self.angular_jerk_limit * dt * (msg.angular.z - self.last_command.angular.z) / abs(msg.angular.z - self.last_command.angular.z) + self.last_acc.angular.z / dt * dt
        # apply velocity limit
        #msg = self.apply_vel_scale_factor(msg, vel_scale_factor)

        # republish message
        self.output_pub.publish(msg)

        # update last timestamp and command
        self.time_old = now
        self.last_command = msg
    
    
    
    def apply_vel_scale_factor(self, msg = Twist(), scale_factor = 1.0):
        msg.linear.x *= scale_factor
        msg.linear.y *= scale_factor
        msg.linear.z *= scale_factor
        msg.angular.x *= scale_factor
        msg.angular.y *= scale_factor
        msg.angular.z *= scale_factor
        return msg
        
    
        
        
        
if __name__ == "__main__":
    UR_twist_limiter().monitor()
        
        