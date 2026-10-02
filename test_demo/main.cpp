#include "test.h"
#include <iostream>

// 旧的全局变量，技术债务示例
int global_buf[100];

void old_func(){
    // 无边界检查，潜在缓冲区溢出
    for(int i=0;i<100;i++){
        global_buf[i] = i;
    }
    std::cout << global_buf[999]; // 越界访问
}

int main(){
    old_func();
    return 0;
}
