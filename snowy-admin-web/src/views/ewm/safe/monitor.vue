<template>
	<div class="safe-container">
		<!-- 头部操作栏 -->
		<div class="mb-4 flex justify-between items-center bg-white p-4 rounded shadow-sm">
			<div class="text-lg font-bold text-gray-800 flex items-center">
				<desktop-outlined class="mr-2 text-primary" />
				<span>设备监控详情</span>
			</div>
			<a-button type="primary" ghost @click="handleClose">
				<template #icon><close-outlined /></template>
				关闭返回
			</a-button>
		</div>

		<!-- 顶部：仪表盘风格的总览 -->
		<a-row :gutter="[16, 16]" class="mb-4">
			<!-- 左侧：基础信息 -->
			<a-col :xs="24" :sm="24" :md="10" :lg="8" :xl="8">
				<a-card :bordered="false" class="h-full info-card">
					<div class="flex flex-col justify-center h-full py-2">
						<div class="flex items-center mb-6 pl-2">
							<div class="avatar-box bg-blue-50 text-blue-500 rounded-full flex items-center justify-center mr-4">
								<desktop-outlined style="font-size: 28px" />
							</div>
							<div class="overflow-hidden">
								<div class="text-xl font-bold text-gray-800 mb-1 truncate" :title="latestInfo?.safeName">
									{{ latestInfo?.safeName || '-' }}
								</div>
								<a-tag :color="isOnline ? 'success' : 'error'" class="border-0">
									<template #icon>
										<span class="w-1.5 h-1.5 rounded-full inline-block mr-1" :class="isOnline ? 'bg-green-500' : 'bg-red-500'"></span>
									</template>
									{{ isOnline ? '在线运行' : '离线' }}
								</a-tag>
							</div>
						</div>

						<div class="info-list px-2">
							<div class="info-item">
								<span class="label">操作系统</span>
								<span class="value" :title="latestInfo?.safeOs">{{ latestInfo?.safeOs || '-' }}</span>
							</div>
							<div class="info-item">
								<span class="label">IP地址</span>
								<span class="value">{{ latestInfo?.safeIp || '-' }}</span>
							</div>
							<div class="info-item">
								<span class="label">CPU型号</span>
								<span class="value" :title="latestInfo?.safeCpu">{{ formatCpuName(latestInfo?.safeCpu) }}</span>
							</div>
							<div class="info-item">
								<span class="label">最后上报</span>
								<span class="value text-xs text-gray-500">{{ formatTime(latestInfo?.createTime) }}</span>
							</div>
						</div>
					</div>
				</a-card>
			</a-col>

			<!-- 右侧：核心指标仪表盘 -->
			<a-col :xs="24" :sm="24" :md="14" :lg="16" :xl="16">
				<a-card :bordered="false" class="h-full" :body-style="{ height: '100%', display: 'flex', alignItems: 'center' }">
					<a-row :gutter="16" class="w-full text-center py-2">
						<!-- CPU -->
						<a-col :span="8">
							<div class="gauge-wrap hover:scale-105 transition-transform duration-300">
								<a-progress
									type="dashboard"
									:percent="parseUsage(latestInfo?.safeCpuUsage)"
									:stroke-color="gradientColor.cpu"
									:width="150"
									:strokeWidth="10"
									:gap-degree="75"
								>
									<template #format="percent">
										<div class="stat-value text-2xl font-bold text-gray-800 text-12">{{ percent }}<span class="text-sm font-normal text-gray-400 ml-1">%</span></div>
										<div class="stat-label text-gray-400 text-xs mt-1 text-12">CPU使用率</div>
									</template>
								</a-progress>
								<div class="mt-2 text-gray-600 font-medium text-sm px-2 cpu-label" :title="latestInfo?.safeCpu">
									{{ formatCpuName(latestInfo?.safeCpu) }}
								</div>
							</div>
						</a-col>
						<!-- 内存 -->
						<a-col :span="8">
							<div class="gauge-wrap hover:scale-105 transition-transform duration-300">
								<a-progress
									type="dashboard"
									:percent="parseUsage(latestInfo?.safeMemoryUsage)"
									:stroke-color="gradientColor.memory"
									:width="150"
									:strokeWidth="10"
									:gap-degree="75"
								>
									<template #format="percent">
										<div class="stat-value text-2xl font-bold text-gray-800 text-12">{{ percent }}<span class="text-sm font-normal text-gray-400 ml-1">%</span></div>
										<div class="stat-label text-gray-400 text-xs mt-1 text-12">内存使用率</div>
									</template>
								</a-progress>
								<div class="mt-2 text-gray-600 font-medium text-sm standard-label">
									总内存: {{ latestInfo?.safeMemory || '-' }}
								</div>
							</div>
						</a-col>
						<!-- 硬盘 -->
						<a-col :span="8">
							<div class="gauge-wrap hover:scale-105 transition-transform duration-300">
								<a-progress
									type="dashboard"
									:percent="parseUsage(latestInfo?.safeDiskUsage)"
									:stroke-color="gradientColor.disk"
									:width="150"
									:strokeWidth="10"
									:gap-degree="75"
								>
									<template #format="percent">
										<div class="stat-value text-2xl font-bold text-gray-800 text-12">{{ percent }}<span class="text-sm font-normal text-gray-400 ml-1">%</span></div>
										<div class="stat-label text-gray-400 text-xs mt-1 text-12">硬盘使用率</div>
									</template>
								</a-progress>
								<div class="mt-2 text-gray-600 font-medium text-sm standard-label">
									总空间: {{ latestInfo?.safeDisk || '-' }}
								</div>
							</div>
						</a-col>
					</a-row>
				</a-card>
			</a-col>
		</a-row>

		<!-- 底部：历史趋势图表 -->
		<a-row :gutter="16">
			<a-col :span="24">
				<a-card :bordered="false" :body-style="{ padding: '24px' }">
					<div class="flex flex-wrap justify-between items-center mb-6 pb-4 border-b border-gray-100">
						<div class="flex items-center">
							<span class="w-1 h-4 bg-primary rounded mr-2"></span>
							<span class="text-lg font-bold text-gray-800">硬件性能趋势 ({{ autoRefresh ? '自动刷新中' : '已暂停' }})</span>
							<a-switch v-model:checked="autoRefresh" size="small" class="ml-3" checked-children="开" un-checked-children="关" @change="handleAutoRefreshChange"/>
						</div>
						<a-radio-group v-model:value="timeRange" button-style="solid" @change="handleTimeChange" class="mt-2 sm:mt-0">
							<a-radio-button value="1h">近1小时</a-radio-button>
							<a-radio-button value="24h">近24小时</a-radio-button>
							<a-radio-button value="7d">近7天</a-radio-button>
						</a-radio-group>
					</div>

					<div v-if="loading" class="absolute inset-0 flex justify-center items-center bg-white bg-opacity-70 z-10" style="margin-top: 60px;">
						<a-spin tip="加载数据中..." />
					</div>

					<div ref="chartRef" style="width: 100%; height: 400px;"></div>
				</a-card>
			</a-col>
		</a-row>
	</div>
</template>

<script setup name="monitor">
import { ref, onMounted, onUnmounted, nextTick, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { DesktopOutlined, CloseOutlined } from '@ant-design/icons-vue'
import ewmProjectSafeApi from "@/api/ewm/ewmProjectSafeApi";
const route = useRoute()
const router = useRouter()
const loading = ref(false)
const timeRange = ref('1h')
const chartRef = ref(null)
const latestInfo = ref(null)
const autoRefresh = ref(true)
const timer = ref(null)

let myChart = null

// 接收路由参数
const safeId = computed(() => route.query.id) // 后端查询用的ID
const safeIdName = computed(() => route.query.name) // 显示用的名称

// 判断是否在线（最后上报时间在2分钟内视为在线）
const isOnline = computed(() => {
	if (!latestInfo.value || !latestInfo.value.createTime) return false
	const lastTime = new Date(latestInfo.value.createTime).getTime()
	const now = new Date().getTime()
	return (now - lastTime) < 2 * 60 * 1000
})

// 仪表盘渐变色
const gradientColor = {
	cpu: { '0%': '#FFD666', '100%': '#FF4D4F' },
	memory: { '0%': '#69C0FF', '100%': '#1890FF' },
	disk: { '0%': '#95DE64', '100%': '#52C41A' }
}

// --- 辅助函数 ---
const parseUsage = (val) => {
	if (!val) return 0
	if (typeof val === 'number') return val
	return parseFloat(val.replace('%', ''))
}

const formatCpuName = (name) => {
	if (!name) return '-'
	return name.split('@')[0].replace('Intel(R) Xeon(R)', 'Xeon').trim()
}

const formatTime = (timeStr) => {
	if (!timeStr) return '-'
	return timeStr.replace('T', ' ')
}

// --- 核心业务 ---
const handleClose = () => {
	// 根据需求跳转到 /ewm/project
	router.push('/ewm/projectsafe')
}

const fetchData = () => {
	if (!safeId.value) return

	// 如果不是第一次加载，不显示全屏loading，体验更好
	if (!latestInfo.value) {
		loading.value = true
	}

	ewmProjectSafeApi.monitor({
		safeId: safeId.value,
		timeRange: timeRange.value
	}).then((res) => {
		const data = res || []
		if (data.length > 0) {
			// 取最后一条作为最新状态
			latestInfo.value = data[data.length - 1]
			renderChart(data)
		} else {
			latestInfo.value = null
			if (myChart) myChart.clear()
		}
	}).finally(() => {
		loading.value = false
	})
}

const renderChart = (data) => {
	if (!chartRef.value) return
	if (!myChart) myChart = echarts.init(chartRef.value)

	const times = data.map(item => {
		// 简单处理时间格式，只显示 MM-dd HH:mm:ss
		const t = item.createTime || ''
		return t.length > 10 ? t.substring(5).replace('T', ' ') : t
	})
	const cpu = data.map(item => parseUsage(item.safeCpuUsage))
	const mem = data.map(item => parseUsage(item.safeMemoryUsage))
	const disk = data.map(item => parseUsage(item.safeDiskUsage))

	const option = {
		color: ['#ff4d4f', '#1890ff', '#52c41a'],
		tooltip: {
			trigger: 'axis',
			backgroundColor: 'rgba(255, 255, 255, 0.96)',
			borderColor: '#f0f0f0',
			borderWidth: 1,
			padding: [10, 14],
			textStyle: { color: '#333', fontSize: 13 },
			extraCssText: 'box-shadow: 0 4px 12px rgba(0,0,0,0.15); border-radius: 6px;',
			formatter: (params) => {
				let html = `<div style="margin-bottom: 8px; font-weight: 600; color: #555;">${params[0].axisValue}</div>`
				params.forEach(item => {
					const dot = `<span style="display:inline-block;margin-right:6px;border-radius:50%;width:8px;height:8px;background-color:${item.color};"></span>`
					html += `
						<div style="display: flex; align-items: center; justify-content: space-between; min-width: 160px; margin-bottom: 4px;">
							<div style="color: #666; font-size: 12px;">${dot}${item.seriesName}</div>
							<div style="font-weight: 700; color: #333;">${item.value}%</div>
						</div>`
				})
				return html
			}
		},
		legend: {
			data: ['CPU使用率', '内存使用率', '硬盘使用率'],
			bottom: 0,
			icon: 'roundRect',
			itemWidth: 12,
			itemHeight: 4
		},
		grid: {
			left: '2%',
			right: '3%',
			bottom: '10%',
			top: '8%',
			containLabel: true
		},
		xAxis: {
			type: 'category',
			boundaryGap: false,
			data: times,
			axisLine: { show: false },
			axisTick: { show: false },
			axisLabel: { color: '#9ca3af', margin: 16 }
		},
		yAxis: {
			type: 'value',
			min: 0,
			max: 100,
			splitLine: { lineStyle: { type: 'dashed', color: '#f0f0f0' } },
			axisLabel: { color: '#9ca3af', formatter: '{value}%' }
		},
		series: [
			{
				name: 'CPU使用率',
				type: 'line',
				smooth: true,
				showSymbol: false,
				lineStyle: { width: 3 },
				areaStyle: {
					opacity: 0.8,
					color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
						{ offset: 0, color: 'rgba(255, 77, 79, 0.25)' },
						{ offset: 1, color: 'rgba(255, 77, 79, 0.01)' }
					])
				},
				data: cpu
			},
			{
				name: '内存使用率',
				type: 'line',
				smooth: true,
				showSymbol: false,
				lineStyle: { width: 3 },
				areaStyle: {
					opacity: 0.8,
					color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
						{ offset: 0, color: 'rgba(24, 144, 255, 0.2)' },
						{ offset: 1, color: 'rgba(24, 144, 255, 0.01)' }
					])
				},
				data: mem
			},
			{
				name: '硬盘使用率',
				type: 'line',
				smooth: true,
				showSymbol: false,
				lineStyle: { width: 3 },
				data: disk
			}
		]
	}
	myChart.setOption(option)
}

const handleTimeChange = () => {
	fetchData()
}

const startTimer = () => {
	stopTimer()
	if (autoRefresh.value) {
		timer.value = setInterval(() => {
			fetchData()
		}, 10000) // 10秒刷新
	}
}

const stopTimer = () => {
	if (timer.value) {
		clearInterval(timer.value)
		timer.value = null
	}
}

const handleAutoRefreshChange = (val) => {
	if (val) {
		startTimer()
		fetchData() // 立即刷新一次
	} else {
		stopTimer()
	}
}

const handleResize = () => {
	myChart && myChart.resize()
}

// --- 生命周期 ---
onMounted(() => {
	nextTick(() => {
		fetchData()
		startTimer()
		window.addEventListener('resize', handleResize)
	})
})

onUnmounted(() => {
	stopTimer()
	window.removeEventListener('resize', handleResize)
	if (myChart) myChart.dispose()
})
</script>

<style scoped lang="less">
.safe-container {
	padding: 16px;
	background-color: #f0f2f5;
	min-height: 100%;
}

.bg-primary {
	background-color: var(--ant-primary-color);
}

.h-full {
	height: 100%;
}
/* CPU 名称多行显示 */
.cpu-label {
	display: -webkit-box;
	-webkit-box-orient: vertical;
	-webkit-line-clamp: 2;
	overflow: hidden;
	text-align: center;
	white-space: normal;
	height: 42px; /* 固定高度，约两行文字 */
	line-height: 1.5;
}
/* 普通标签单行显示但高度一致 */
.standard-label {
	height: 42px;
	display: flex;
	align-items: center;
	justify-content: center;
}
/* 左侧卡片样式 */
.info-card {
	.avatar-box {
		width: 56px;
		height: 56px;
		background: #e6f7ff;
		color: #1890ff;
		flex-shrink: 0;
	}

	.info-list {
		margin-top: 20px;
		.info-item {
			display: flex;
			justify-content: space-between;
			align-items: center;
			padding: 12px 0;
			border-bottom: 1px solid #f5f5f5;
			&:last-child {
				border-bottom: none;
			}
			.label {
				color: #8c8c8c;
				font-size: 14px;
				flex-shrink: 0;
			}
			.value {
				color: #262626;
				font-weight: 500;
				max-width: 65%;
				overflow: hidden;
				text-overflow: ellipsis;
				white-space: nowrap;
				text-align: right;
			}
		}
	}
}

/* 进度条动画容器 */
.gauge-wrap {
	display: flex;
	flex-direction: column;
	align-items: center;
	padding: 10px;
	border-radius: 8px;
	transition: all 0.3s;

	/* 修复 Antd Dashboard 进度条默认文字样式 */
	:deep(.ant-progress-text) {
		display: flex;
		flex-direction: column;
		justify-content: center;
	}
}
</style>
