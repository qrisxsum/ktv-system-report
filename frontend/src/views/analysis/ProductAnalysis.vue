<template>
  <div class="product-analysis">
    <el-card>
      <template #header>
        <span>🍺 商品销售分析</span>
      </template>
      
      <el-table :data="productData" stripe border>
        <el-table-column prop="product_name" label="商品名称" width="150" />
        <el-table-column prop="category" label="类别" width="100" />
        <el-table-column prop="sales_qty" label="销售数量" width="100" align="right" />
        <el-table-column prop="sales_amount" label="销售金额" width="120" align="right">
          <template #default="{ row }">
            ¥{{ row.sales_amount.toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="cost" label="成本" width="100" align="right">
          <template #default="{ row }">
            ¥{{ row.cost.toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="profit" label="利润" width="120" align="right">
          <template #default="{ row }">
            ¥{{ row.profit.toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="profit_rate" label="利润率" width="100" align="right">
          <template #default="{ row }">
            {{ row.profit_rate.toFixed(2) }}%
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const productData = ref([
  { product_name: '青岛崂山', category: '啤酒', sales_qty: 308, sales_amount: 5765.56, cost: 746.67, profit: 5018.89, profit_rate: 672.17 },
  { product_name: '什锦果盘', category: '群果荟萃', sales_qty: 9, sales_amount: 995.62, cost: 10, profit: 985.62, profit_rate: 9856.16 },
  { product_name: '百岁山', category: '饮料', sales_qty: 27, sales_amount: 298.07, cost: 38.94, profit: 259.13, profit_rate: 665.41 },
  { product_name: '卤水花生', category: '卤味小吃', sales_qty: 10, sales_amount: 312.46, cost: 12, profit: 300.46, profit_rate: 2503.85 },
  { product_name: '香辣腐竹', category: '卤味小吃', sales_qty: 11, sales_amount: 323.86, cost: 0, profit: 323.86, profit_rate: 0 },
])
</script>

<style lang="scss" scoped>
.product-analysis {
  // 样式
}
</style>

