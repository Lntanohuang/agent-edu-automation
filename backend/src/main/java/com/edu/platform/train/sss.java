package com.edu.platform.train;

import java.util.HashSet;
import java.util.List;

class Solution {
    public boolean wordBreak(String s, List<String> wordDict) {
        //字典进哈希
        //判断有没有 有就继续 没有就累计
        //遍历完饭回true
        //最后返回false
        HashSet<String> set = new HashSet<>(wordDict);
        char c[]=s.toCharArray();
        int start=0;
        int end=0;

        boolean []dp=new boolean [c.length+1];
        for (int i = 1; i <=c.length ; i++) {
            for (int j = 0; j <i ; j++) {
                if(dp[j]&&set.contains(s.substring(j,i))){
                    dp[i]=true;
                    break;
                }
            }
        }

        return dp[c.length];

    }
}