/*
 * Copyright 2026 Confluent Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import javax.management.MBeanServerConnection;
import javax.management.ObjectName;
import javax.management.remote.JMXConnector;
import javax.management.remote.JMXConnectorFactory;
import javax.management.remote.JMXServiceURL;

/**
 * Attempts an unauthenticated remote JMX connection to host:port and reports
 * whether the MBean server was reachable.
 *
 * <p>Run from a container other than the one under test, so that "reachable"
 * means genuinely reachable across the network rather than over loopback.
 */
public class JmxProbe {
  public static void main(String[] args) {
    if (args.length != 1) {
      System.out.println("usage: JmxProbe <host:port>");
      System.exit(2);
    }
    String target = args[0];
    String url = "service:jmx:rmi:///jndi/rmi://" + target + "/jmxrmi";
    try {
      JMXConnector connector = JMXConnectorFactory.connect(new JMXServiceURL(url), null);
      MBeanServerConnection mbeans = connector.getMBeanServerConnection();
      String vmName =
          (String) mbeans.getAttribute(new ObjectName("java.lang:type=Runtime"), "Name");
      System.out.println("JMX_RESULT=REACHABLE"
          + " target=" + target
          + " mbeanCount=" + mbeans.getMBeanCount()
          + " remoteVm=" + vmName);
      connector.close();
    } catch (Exception e) {
      System.out.println("JMX_RESULT=UNREACHABLE"
          + " target=" + target
          + " cause=" + e.getClass().getSimpleName()
          + ": " + String.valueOf(e.getMessage()).replace('\n', ' '));
    }
  }
}
