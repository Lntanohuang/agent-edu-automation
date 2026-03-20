package com.edu.platform.chat;

import com.edu.platform.chat.mongo.ChatMessageArchiveRepository;
import com.edu.platform.chat.service.ChatMongoArchiveService;
import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.test.context.ActiveProfiles;

import java.util.Set;

/**
 * 集成测试基类：
 * - 激活 test profile（H2 + Redis db=1 + 真实 RabbitMQ）
 * - MongoDB 通过 application-test.yml 排除自动配置，用 @MockBean 替代
 * - 每个测试前清理 Redis db=1 中的 chat:* key
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@ActiveProfiles("test")
public abstract class BaseIntegrationTest {

    @Autowired
    protected StringRedisTemplate redisTemplate;

    @MockBean
    protected ChatMongoArchiveService mongoArchiveService;

    @MockBean
    protected ChatMessageArchiveRepository archiveRepository;

    @BeforeEach
    void cleanRedisTestKeys() {
        Set<String> keys = redisTemplate.keys("chat:*");
        if (keys != null && !keys.isEmpty()) {
            redisTemplate.delete(keys);
        }
    }
}
