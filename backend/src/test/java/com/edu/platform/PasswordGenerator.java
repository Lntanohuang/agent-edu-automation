package com.edu.platform;

import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;

public class PasswordGenerator {
    public static void main(String[] args) {
        BCryptPasswordEncoder encoder = new BCryptPasswordEncoder();
        
        String[] passwords = {"admin123", "teacher123", "test123"};
        
        for (String pwd : passwords) {
            String hash = encoder.encode(pwd);
            System.out.println(pwd + " -> " + hash);
        }
    }
}
