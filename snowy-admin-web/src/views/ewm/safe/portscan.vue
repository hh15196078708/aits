<template>
	<a-card :bordered="false">
		<!-- 页面头部：如果是从客户端列表点进来的，显示返回按钮和当前终端ID -->
		<a-page-header
			v-if="route.query.safeId"
			title="端口扫描记录"
			@back="goBack"
			class="pb-0"
		>
			<template #subTitle>
				当前监控终端: <a-tag color="blue">{{ route.query.safeId }}</a-tag>
			</template>
		</a-page-header>

		<!-- 搜索表单 -->
		<a-form ref="searchFormRef" name="advanced_search" :model="searchFormState" class="ant-advanced-search-form">
			<a-row :gutter="24">
				<a-col :span="6">
					<a-form-item label="源IP" name="sourceIp">
						<a-input v-model:value="searchFormState.sourceIp" placeholder="请输入攻击源IP" allow-clear />
					</a-form-item>
				</a-col>
				<a-col :span="6">
					<a-form-item label="威胁等级" name="level">
						<a-select v-model:value="searchFormState.level" placeholder="请选择威胁等级" allow-clear>
							<a-select-option value="高危">高危</a-select-option>
							<a-select-option value="中危">中危</a-select-option>
							<a-select-option value="低危">低危</a-select-option>
						</a-select>
					</a-form-item>
				</a-col>
				<a-col :span="6">
					<a-form-item label="扫描类型" name="scanType">
						<a-input v-model:value="searchFormState.scanType" placeholder="例如: SYN Scan" allow-clear />
					</a-form-item>
				</a-col>
				<a-col :span="6">
					<a-button type="primary" @click="tableRef.refresh(true)">查询</a-button>
					<a-button style="margin-left: 8px" @click="reset">重置</a-button>
				</a-col>
			</a-row>
		</a-form>

		<!-- 数据表格：自带翻页功能 -->
		<s-table
			ref="tableRef"
			:columns="columns"
			:data="loadData"
			:alert="false"
			bordered
			:row-key="(record) => record.id"
		>
			<template #bodyCell="{ column, record }">
				<!-- 威胁等级 颜色标签 -->
				<template v-if="column.dataIndex === 'level'">
					<a-tag :color="getLevelColor(record.level)">
						{{ record.level }}
					</a-tag>
				</template>
				<!-- 目标端口 气泡提示 (防止端口过多撑破表格) -->
				<template v-if="column.dataIndex === 'targetPorts'">
					<a-tooltip :title="record.targetPorts" placement="topLeft">
						<div class="truncate" style="max-width: 150px;">{{ record.targetPorts }}</div>
					</a-tooltip>
				</template>
			</template>
		</s-table>
	</a-card>
</template>

<script setup name="AttackPortScanIndex">
import { ref, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import attackPortScanApi from '@/api/ewm/portscan'

const route = useRoute()
const router = useRouter()

const tableRef = ref()
const searchFormRef = ref()
const searchFormState = reactive({
	sourceIp: '',
	level: '',
	scanType: ''
})

// 表头定义与 AttackPortScan 实体属性对应
const columns = [
	{ title: '攻击时间', dataIndex: 'attackTime', sorter: true, width: 170 },
	{ title: '终端ID', dataIndex: 'safeId', width: 120 },
	{ title: '攻击类型', dataIndex: 'attackType', width: 120 },
	{ title: '扫描类型', dataIndex: 'scanType', width: 120 },
	{ title: '源IP', dataIndex: 'sourceIp', width: 130 },
	{ title: '威胁等级', dataIndex: 'level', width: 90, align: 'center' },
	{ title: '检测方法', dataIndex: 'detectionMethod', width: 120 },
	{ title: '目标端口', dataIndex: 'targetPorts', width: 160 },
	{ title: '持续时间', dataIndex: 'duration', width: 100 }
]

// 加载表格数据
const loadData = (parameter) => {
	const requestParameters = Object.assign({}, parameter, searchFormState)

	// 【核心逻辑】如果从客户端列表跳转过来，路由里会有 safeId，将其加入查询条件
	if (route.query.safeId) {
		requestParameters.safeId = route.query.safeId
	}

	// MongoDB 查询通常接收 page, size 或 pageNo, pageSize，这里交给框架底层的 s-table 和 axios 处理
	return attackPortScanApi.attackPortScanPage(requestParameters).then((data) => {
		return data
	})
}

// 重置查询
const reset = () => {
	searchFormRef.value.resetFields()
	tableRef.value.refresh(true)
}

// 返回上一页 (客户端列表)
const goBack = () => {
	router.back()
}

// 根据威胁等级返回不同颜色
const getLevelColor = (level) => {
	if (!level) return 'default'
	if (level.includes('高')) return 'red'
	if (level.includes('中')) return 'orange'
	if (level.includes('低')) return 'green'
	return 'blue'
}
</script>

<style scoped>
.truncate {
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}
</style>
