<template>
  <div class="room-analysis">
    <el-card>
      <template #header>
        <span>🎤 包厢效能分析</span>
      </template>
      
      <el-row :gutter="20" class="summary-cards">
        <el-col :span="6">
          <div class="summary-item">
            <div class="label">总开台数</div>
            <div class="value">78</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="summary-item">
            <div class="label">平均消费时长</div>
            <div class="value">312 分钟</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="summary-item">
            <div class="label">平均消费金额</div>
            <div class="value">¥298.74</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="summary-item">
            <div class="label">总营收</div>
            <div class="value">¥23,302</div>
          </div>
        </el-col>
      </el-row>
      
      <el-table :data="roomData" stripe border style="margin-top: 20px">
        <el-table-column prop="room_type" label="包厢类型" width="120" />
        <el-table-column prop="count" label="开台次数" width="100" align="right" />
        <el-table-column prop="total_amount" label="总金额" width="120" align="right">
          <template #default="{ row }">
            ¥{{ row.total_amount.toLocaleString() }}
          </template>
        </el-table-column>
        <el-table-column prop="avg_duration" label="平均时长" width="100" align="right">
          <template #default="{ row }">
            {{ row.avg_duration }} 分钟
          </template>
        </el-table-column>
        <el-table-column prop="avg_amount" label="平均消费" align="right">
          <template #default="{ row }">
            ¥{{ row.avg_amount.toFixed(2) }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const roomData = ref([
  { room_type: '电音中包', count: 42, total_amount: 12500, avg_duration: 285, avg_amount: 297.62 },
  { room_type: '电音小包', count: 18, total_amount: 3200, avg_duration: 310, avg_amount: 177.78 },
  { room_type: '电音大包', count: 12, total_amount: 5800, avg_duration: 345, avg_amount: 483.33 },
  { room_type: '派对包', count: 6, total_amount: 1802, avg_duration: 380, avg_amount: 300.33 },
])
</script>

<style lang="scss" scoped>
.room-analysis {
  .summary-cards {
    .summary-item {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      border-radius: 8px;
      padding: 20px;
      color: #fff;
      text-align: center;
      
      .label {
        font-size: 14px;
        opacity: 0.9;
        margin-bottom: 8px;
      }
      
      .value {
        font-size: 24px;
        font-weight: bold;
      }
    }
  }
}
</style>

