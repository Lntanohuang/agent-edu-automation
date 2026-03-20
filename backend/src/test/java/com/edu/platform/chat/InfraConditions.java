package com.edu.platform.chat;

import java.net.Socket;

/**
 * 基础设施可用性检测，用于集成测试的条件跳过。
 */
public final class InfraConditions {

    private InfraConditions() {}

    public static boolean isRedisAvailable() {
        return isPortOpen("localhost", 6379);
    }

    public static boolean isRabbitMqAvailable() {
        return isPortOpen("localhost", 5672);
    }

    private static boolean isPortOpen(String host, int port) {
        try (Socket socket = new Socket(host, port)) {
            return true;
        } catch (Exception e) {
            return false;
        }
    }
}
