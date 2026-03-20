package com.edu.platform.chat.service;

import com.edu.platform.chat.mongo.ChatMessageArchive;
import com.edu.platform.chat.mongo.ChatMessageArchiveRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class ChatMongoArchiveService {

    private final ChatMessageArchiveRepository archiveRepository;

    @Async
    public void archiveBatch(List<ChatMessageArchive> archives) {
        if (archives == null || archives.isEmpty()) {
            return;
        }
        try {
            archiveRepository.saveAll(archives);
        } catch (DuplicateKeyException duplicateKeyException) {
            log.warn("Mongo 归档去重命中: {}", duplicateKeyException.getMessage());
        } catch (Exception e) {
            log.error("Mongo 归档失败", e);
        }
    }
}
