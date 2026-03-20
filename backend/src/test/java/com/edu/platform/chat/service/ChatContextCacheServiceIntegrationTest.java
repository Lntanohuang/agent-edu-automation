package com.edu.platform.chat.service;

import com.edu.platform.chat.BaseIntegrationTest;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Redis 集成测试 — 连接真实 Redis (db=1)。
 * 每个测试打印 Redis 中的原始数据，让你直观看到缓存行为。
 */
@DisplayName("【Redis 集成】ChatContextCacheService")
class ChatContextCacheServiceIntegrationTest extends BaseIntegrationTest {

    @Autowired
    private ChatContextCacheService cacheService;

    // ========== 聊天历史缓存 ==========

    @Test
    @DisplayName("写入消息后可以从 Redis 读到原始 JSON")
    void appendUserMessage_andVerifyRawKeyInRedis() {
        cacheService.appendUserMessage(1L, "什么是法律渊源？");

        List<String> raw = redisTemplate.opsForList().range("chat:session:1:messages", 0, -1);
        System.out.println("\n========== [Redis 原始数据] ==========");
        System.out.println("Key: chat:session:1:messages");
        System.out.println("Value: " + raw);
        System.out.println("======================================\n");

        assertThat(raw).hasSize(1);
        assertThat(raw.get(0)).contains("什么是法律渊源？").contains("\"role\":\"user\"");
    }

    @Test
    @DisplayName("超过 historyWindow(10) 后自动 trim")
    void appendMultipleMessages_trimToHistoryWindow() {
        for (int i = 1; i <= 15; i++) {
            cacheService.appendUserMessage(2L, "消息 #" + i);
        }

        Long size = redisTemplate.opsForList().size("chat:session:2:messages");
        List<String> raw = redisTemplate.opsForList().range("chat:session:2:messages", 0, -1);

        System.out.println("\n========== [Redis 窗口裁剪] ==========");
        System.out.println("写入了 15 条消息，historyWindow=10");
        System.out.println("实际 Redis list 长度: " + size);
        System.out.println("最早一条: " + (raw != null && !raw.isEmpty() ? raw.get(0) : "空"));
        System.out.println("最新一条: " + (raw != null && !raw.isEmpty() ? raw.get(raw.size() - 1) : "空"));
        System.out.println("======================================\n");

        assertThat(size).isEqualTo(10);
        // 最早的 5 条（#1~#5）已被 trim 掉，第一条应该是 #6
        assertThat(raw.get(0)).contains("消息 #6");
    }

    // ========== 幂等去重 ==========

    @Test
    @DisplayName("首次标记返回 true，重复标记返回 false（SETNX 幂等）")
    void markEventProcessed_idempotency() {
        boolean first = cacheService.markEventProcessed("test-evt-001");
        boolean second = cacheService.markEventProcessed("test-evt-001");

        String value = redisTemplate.opsForValue().get("chat:msg:digest:test-evt-001");
        Long ttl = redisTemplate.getExpire("chat:msg:digest:test-evt-001", TimeUnit.SECONDS);

        System.out.println("\n========== [Redis 幂等去重] ==========");
        System.out.println("Key: chat:msg:digest:test-evt-001");
        System.out.println("Value: " + value);
        System.out.println("TTL: " + ttl + " 秒 (约 " + (ttl != null ? ttl / 86400 : "?") + " 天)");
        System.out.println("第一次调用: " + first + " (应为 true)");
        System.out.println("第二次调用: " + second + " (应为 false，被去重)");
        System.out.println("======================================\n");

        assertThat(first).isTrue();
        assertThat(second).isFalse();
        assertThat(value).isEqualTo("1");
    }

    @Test
    @DisplayName("clearEventDigest 后可重新处理")
    void clearEventDigest_allowsReprocessing() {
        cacheService.markEventProcessed("test-evt-clear");
        assertThat(redisTemplate.hasKey("chat:msg:digest:test-evt-clear")).isTrue();

        cacheService.clearEventDigest("test-evt-clear");
        assertThat(redisTemplate.hasKey("chat:msg:digest:test-evt-clear")).isFalse();

        boolean again = cacheService.markEventProcessed("test-evt-clear");

        System.out.println("\n========== [Redis 幂等重置] ==========");
        System.out.println("清除 digest 后重新标记: " + again + " (应为 true)");
        System.out.println("======================================\n");

        assertThat(again).isTrue();
    }

    // ========== 会话元信息 ==========

    @Test
    @DisplayName("追加消息后 meta hash 中有 last_active_at，且设置了 TTL")
    void touchConversation_setsMetaAndTTL() {
        cacheService.appendUserMessage(3L, "触发 touch");

        Map<Object, Object> meta = redisTemplate.opsForHash().entries("chat:session:3:meta");
        Long historyTtl = redisTemplate.getExpire("chat:session:3:messages", TimeUnit.SECONDS);
        Long metaTtl = redisTemplate.getExpire("chat:session:3:meta", TimeUnit.SECONDS);

        System.out.println("\n========== [Redis 会话元信息] ==========");
        System.out.println("Meta hash: " + meta);
        System.out.println("History TTL: " + historyTtl + " 秒");
        System.out.println("Meta TTL: " + metaTtl + " 秒");
        System.out.println("========================================\n");

        assertThat(meta).containsKey("last_active_at");
        assertThat(historyTtl).isGreaterThan(0);
        assertThat(metaTtl).isGreaterThan(0);
    }

    // ========== 清空会话 ==========

    @Test
    @DisplayName("clearConversation 删除 history 和 meta 两个 key")
    void clearConversation_deletesAllKeys() {
        cacheService.appendUserMessage(4L, "即将被清空");
        assertThat(redisTemplate.hasKey("chat:session:4:messages")).isTrue();
        assertThat(redisTemplate.hasKey("chat:session:4:meta")).isTrue();

        cacheService.clearConversation(4L);

        System.out.println("\n========== [Redis 清空会话] ==========");
        System.out.println("chat:session:4:messages 存在: " + redisTemplate.hasKey("chat:session:4:messages"));
        System.out.println("chat:session:4:meta 存在: " + redisTemplate.hasKey("chat:session:4:meta"));
        System.out.println("======================================\n");

        assertThat(redisTemplate.hasKey("chat:session:4:messages")).isFalse();
        assertThat(redisTemplate.hasKey("chat:session:4:meta")).isFalse();
    }
}
