package com.edu.platform.chat.mongo;

import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface ChatMessageArchiveRepository extends MongoRepository<ChatMessageArchive, String> {
}
