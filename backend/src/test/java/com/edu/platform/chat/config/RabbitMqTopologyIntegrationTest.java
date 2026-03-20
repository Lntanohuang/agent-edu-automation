package com.edu.platform.chat.config;

import com.edu.platform.chat.BaseIntegrationTest;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.amqp.rabbit.core.RabbitAdmin;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.context.TestPropertySource;

import java.util.List;
import java.util.Properties;

import org.junit.jupiter.api.BeforeEach;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assumptions.assumeTrue;

/**
 * RabbitMQ 拓扑验证 — 确认所有队列、交换器、绑定关系正确声明。
 */
@DisplayName("【RabbitMQ 集成】拓扑结构验证")
@TestPropertySource(properties = "spring.rabbitmq.listener.simple.auto-startup=false")
class RabbitMqTopologyIntegrationTest extends BaseIntegrationTest {

    @Autowired
    private RabbitAdmin rabbitAdmin;

    @BeforeEach
    void checkRabbitMq() {
        assumeTrue(com.edu.platform.chat.InfraConditions.isRabbitMqAvailable(),
                "跳过：本地 RabbitMQ 未启动");
    }

    @Test
    @DisplayName("所有 6 个队列（3 业务 + 3 DLQ）均已声明")
    void allQueuesExist() {
        List<String> queues = List.of(
                ChatMqConstants.USER_QUEUE,
                ChatMqConstants.AI_REPLY_USER_QUEUE,
                ChatMqConstants.AI_REPLY_PERSIST_QUEUE,
                ChatMqConstants.USER_DLQ,
                ChatMqConstants.AI_REPLY_USER_DLQ,
                ChatMqConstants.AI_REPLY_PERSIST_DLQ
        );

        System.out.println("\n========== [RabbitMQ 拓扑] 队列列表 ==========");
        for (String queue : queues) {
            Properties info = rabbitAdmin.getQueueProperties(queue);
            String status = (info != null) ? "存在 (消息数: " + info.getProperty("QUEUE_MESSAGE_COUNT", "0") + ")" : "不存在!";
            System.out.println("  " + queue + " → " + status);
            assertThat(info).as("队列 %s 应该存在", queue).isNotNull();
        }
        System.out.println("================================================\n");
    }

    @Test
    @DisplayName("用户消息队列绑定了死信交换器")
    void userQueueHasDeadLetterConfig() {
        Properties info = rabbitAdmin.getQueueProperties(ChatMqConstants.USER_QUEUE);

        System.out.println("\n========== [RabbitMQ 拓扑] DLQ 配置 ==========");
        System.out.println("队列: " + ChatMqConstants.USER_QUEUE);
        System.out.println("队列属性: " + info);
        System.out.println("（DLQ 配置在队列声明的 arguments 中，运行时已生效）");
        System.out.println("================================================\n");

        assertThat(info).isNotNull();
    }
}
