<template>
  <div class="login-container">
    <div class="login-card">
      <!-- Logo 和标题 -->
      <div class="login-header">
        <el-icon size="60" class="logo-icon"><Microphone /></el-icon>
        <h1 class="title">KTV 经营分析系统</h1>
        <p class="subtitle">登录您的账户</p>
      </div>

      <!-- 登录表单 -->
      <el-form
        ref="loginFormRef"
        :model="loginForm"
        :rules="loginRules"
        label-position="top"
        class="login-form"
      >
        <el-form-item label="用户名" prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="请输入用户名"
            size="large"
            :prefix-icon="User"
            clearable
          />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="请输入密码"
            size="large"
            :prefix-icon="Lock"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            size="large"
            class="login-btn"
            :loading="loading"
            @click="handleLogin"
          >
            {{ loading ? '登录中...' : '登录' }}
          </el-button>
        </el-form-item>
      </el-form>

      <!-- 演示账号提示 -->
      <div class="demo-accounts">
        <p class="demo-title">演示账号：</p>
        <div class="account-list">
          <div class="account-item">
            <strong>管理员：</strong> admin / admin123
          </div>
          <div class="account-item">
            <strong>店长：</strong> manager / manager123
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock, Microphone } from '@element-plus/icons-vue'
import { login } from '@/api/auth'

const router = useRouter()

// 表单引用
const loginFormRef = ref()

// 登录表单数据
const loginForm = reactive({
  username: '',
  password: ''
})

// 表单验证规则
const loginRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' }
  ]
}

// 加载状态
const loading = ref(false)

// 登录处理
const handleLogin = async () => {
  try {
    // 表单验证
    await loginFormRef.value.validate()

    loading.value = true

    // 调用登录API
    console.log('开始登录请求:', { username: loginForm.username, password: '***' })
    const response = await login(loginForm.username, loginForm.password)
    console.log('登录API响应:', response)

    if (response.success) {
      // 保存token和用户信息到本地存储
      const token = response.token || ''
      const user = response.user

      localStorage.setItem('access_token', token)
      localStorage.setItem('user', JSON.stringify(user))

      console.log('登录成功，保存token和用户信息:', {
        token: token,
        user: user,
        localStorage_token: localStorage.getItem('access_token'),
        localStorage_user: localStorage.getItem('user')
      })

      ElMessage.success('登录成功')

      // 延迟一下确保数据保存完成
      await new Promise(resolve => setTimeout(resolve, 100))

      // 验证数据是否正确保存
      const savedToken = localStorage.getItem('access_token')
      const savedUser = localStorage.getItem('user')

      console.log('验证保存的数据:', {
        savedToken: !!savedToken,
        savedUser: !!savedUser,
        tokenLength: savedToken?.length,
        userParsed: savedUser ? JSON.parse(savedUser) : null
      })

      // 跳转到首页
      console.log('跳转到dashboard页面')
      console.log('当前路由:', router.currentRoute.value)

      try {
        console.log('开始路由跳转...')
        const result = await router.push('/dashboard')
        console.log('路由跳转结果:', result)
        console.log('跳转后路由:', router.currentRoute.value)

        // 等待一小段时间，确保页面加载完成
        await new Promise(resolve => setTimeout(resolve, 500))

        console.log('页面应该已经跳转完成')
      } catch (error) {
        console.error('路由跳转失败:', error)
        // 如果路由跳转失败，强制刷新页面
        console.log('尝试强制跳转...')
        window.location.href = '/#/dashboard'
      }
    }
  } catch (error) {
    console.error('登录失败:', error)
    console.error('错误详情:', error.response?.data)
    // 显示具体的错误信息
    // 优先显示后端返回的详细错误信息（如"账号已停用"）
    let errorMessage = '登录失败，请检查用户名和密码'
    if (error.response?.data?.detail) {
      errorMessage = error.response.data.detail
    } else if (error.response?.data?.message) {
      errorMessage = error.response.data.message
    } else if (error.message) {
      errorMessage = error.message
    }
    ElMessage.error(errorMessage)
  } finally {
    loading.value = false
  }
}
</script>

<style lang="scss" scoped>
.login-container {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.login-card {
  width: 100%;
  max-width: 400px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
  padding: 40px;
  text-align: center;
}

.login-header {
  margin-bottom: 30px;

  .logo-icon {
    color: #667eea;
    margin-bottom: 15px;
  }

  .title {
    font-size: 24px;
    font-weight: 600;
    color: #333;
    margin: 0 0 8px 0;
  }

  .subtitle {
    color: #666;
    margin: 0;
    font-size: 14px;
  }
}

.login-form {
  margin-bottom: 30px;

  :deep(.el-form-item__label) {
    font-weight: 500;
    color: #333;
    margin-bottom: 8px;
  }

  :deep(.el-input__wrapper) {
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }
}

.login-btn {
  width: 100%;
  height: 48px;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 500;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;

  &:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
  }
}

.demo-accounts {
  text-align: left;
  padding-top: 20px;
  border-top: 1px solid #f0f0f0;

  .demo-title {
    font-size: 14px;
    color: #666;
    margin: 0 0 10px 0;
    font-weight: 500;
  }

  .account-list {
    .account-item {
      font-size: 13px;
      color: #666;
      margin-bottom: 5px;

      strong {
        color: #333;
      }
    }
  }
}

// 响应式设计
@media (max-width: 768px) {
  .login-container {
    padding: 15px;
  }

  .login-card {
    padding: 35px 25px;
  }

  .login-header {
    margin-bottom: 25px;

    .logo-icon {
      font-size: 50px !important;
    }

    .title {
      font-size: 22px;
    }
  }

  .demo-accounts {
    .demo-title {
      font-size: 13px;
    }

    .account-list .account-item {
      font-size: 12px;
    }
  }
}

@media (max-width: 480px) {
  .login-card {
    padding: 30px 20px;
  }

  .login-header {
    .logo-icon {
      font-size: 45px !important;
    }

    .title {
      font-size: 20px;
    }

    .subtitle {
      font-size: 13px;
    }
  }

  .login-btn {
    height: 44px;
    font-size: 15px;
  }
}
</style>
