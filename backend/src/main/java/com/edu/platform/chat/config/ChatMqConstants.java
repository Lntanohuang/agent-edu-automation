package com.edu.platform.chat.config;

public final class ChatMqConstants {

    private ChatMqConstants() {
    }

    public static final String USER_EXCHANGE = "chat.user.exchange";
    public static final String USER_QUEUE = "chat.user.queue";
    public static final String USER_ROUTING_KEY = "chat.user.msg";

    public static final String AI_EXCHANGE = "chat.ai.exchange";
    public static final String AI_REPLY_USER_QUEUE = "chat.ai.reply.user.queue";
    public static final String AI_REPLY_PERSIST_QUEUE = "chat.ai.reply.persist.queue";
    public static final String AI_ROUTING_KEY = "chat.ai.reply";

    public static final String USER_DLX_EXCHANGE = "chat.user.dlx.exchange";
    public static final String USER_DLQ = "chat.user.dlq";
    public static final String USER_DLQ_ROUTING_KEY = "chat.user.dlq";

    public static final String AI_DLX_EXCHANGE = "chat.ai.dlx.exchange";
    public static final String AI_REPLY_USER_DLQ = "chat.ai.reply.user.dlq";
    public static final String AI_REPLY_PERSIST_DLQ = "chat.ai.reply.persist.dlq";
    public static final String AI_REPLY_USER_DLQ_ROUTING_KEY = "chat.ai.reply.user.dlq";
    public static final String AI_REPLY_PERSIST_DLQ_ROUTING_KEY = "chat.ai.reply.persist.dlq";
}
