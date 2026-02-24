<template>
	<xn-form-container
		title="终端安全配置"
		:width="700"
		:visible="visible"
		:destroy-on-close="true"
		@close="onClose"
	>
		<a-form ref="formRef" :model="formData" layout="vertical">
			<!-- IP安全策略 -->
			<a-divider orientation="left">IP安全策略</a-divider>
			<a-row :gutter="16">
				<a-col :span="12">
					<a-form-item label="是否开启IP自动拉黑：">
						<a-switch v-model:checked="formData.ipBlockerEnabled" checked-children="开启" un-checked-children="关闭" />
					</a-form-item>
				</a-col>
			</a-row>
			<a-row :gutter="16">
				<a-col :span="24">
					<a-form-item label="IP白名单：">
						<a-select
							v-model:value="formData.ipWhitelist"
							mode="tags"
							placeholder="输入IP地址后按回车添加，如：192.168.1.1"
							:token-separators="[',', ' ']"
							allow-clear
						/>
					</a-form-item>
				</a-col>
			</a-row>

			<!-- Web日志配置 -->
			<a-divider orientation="left">Web日志配置</a-divider>
			<div class="web-log-section">
				<a-row
					v-for="(item, index) in formData.webLogSources"
					:key="index"
					:gutter="8"
					class="mb-2"
					align="middle"
				>
					<a-col :span="10">
						<a-input v-model:value="item.path" placeholder="日志文件路径" />
					</a-col>
					<a-col :span="6">
						<a-select v-model:value="item.type" placeholder="类型">
							<a-select-option value="nginx">Nginx</a-select-option>
							<a-select-option value="apache">Apache</a-select-option>
							<a-select-option value="iis">IIS</a-select-option>
							<a-select-option value="tomcat">Tomcat</a-select-option>
						</a-select>
					</a-col>
					<a-col :span="4">
						<a-switch v-model:checked="item.enabled" checked-children="启用" un-checked-children="禁用" size="small" />
					</a-col>
					<a-col :span="4" class="text-center">
						<MinusCircleOutlined
							v-if="formData.webLogSources.length > 1"
							class="dynamic-delete-button"
							@click="removeWebLogSource(index)"
						/>
						<PlusOutlined
							v-if="index === formData.webLogSources.length - 1"
							class="dynamic-add-button ml-2"
							@click="addWebLogSource"
						/>
					</a-col>
				</a-row>
				<a-button
					v-if="formData.webLogSources.length === 0"
					type="dashed"
					block
					@click="addWebLogSource"
				>
					<PlusOutlined /> 添加Web日志路径
				</a-button>
			</div>

			<!-- 流量嗅探配置 -->
			<a-divider orientation="left">流量嗅探配置</a-divider>
			<a-row :gutter="16">
				<a-col :span="12">
					<a-form-item label="是否开启流量嗅探抓包：">
						<a-switch v-model:checked="formData.snifferEnabled" checked-children="开启" un-checked-children="关闭" />
					</a-form-item>
				</a-col>
			</a-row>
			<a-row :gutter="16">
				<a-col :span="24">
					<a-form-item label="嗅探采集端口：">
						<a-select
							v-model:value="formData.snifferPorts"
							mode="tags"
							placeholder="输入端口号后按回车添加，如：80、443、8080"
							:token-separators="[',', ' ']"
							allow-clear
						/>
					</a-form-item>
				</a-col>
			</a-row>
			<a-row :gutter="16">
				<a-col :span="12">
					<a-form-item label="攻击日志上报间隔（秒）：">
						<a-input-number
							v-model:value="formData.attackLogUploadInterval"
							:min="1"
							:max="3600"
							placeholder="默认30秒"
							style="width: 100%"
						/>
					</a-form-item>
				</a-col>
			</a-row>
		</a-form>
		<template #footer>
			<a-button style="margin-right: 8px" @click="onClose">关闭</a-button>
			<a-button type="primary" :loading="submitLoading" @click="onSubmit">保存</a-button>
			<a-button @click="onDownload" :loading="downloadLoading">
				<template #icon><DownloadOutlined /></template>
				下载配置
			</a-button>
		</template>
	</xn-form-container>
</template>

<script setup>
import { ref } from 'vue'
import { message } from 'ant-design-vue'
import { PlusOutlined, MinusCircleOutlined, DownloadOutlined } from '@ant-design/icons-vue'
import ewmProjectSafeApi from '@/api/ewm/ewmProjectSafeApi'
import sysConfig from '@/config/index'

const visible = ref(false)
const formRef = ref()
const submitLoading = ref(false)
const downloadLoading = ref(false)
const currentSafeId = ref('')

// 表单数据（含默认值）
const formData = ref({
	ipBlockerEnabled: false,
	ipWhitelist: [],
	webLogSources: [],
	snifferEnabled: true,
	snifferPorts: ['80', '443', '8080', '8443'],
	attackLogUploadInterval: 30
})

// 默认值常量
const defaultFormData = () => ({
	ipBlockerEnabled: false,
	ipWhitelist: [],
	webLogSources: [],
	snifferEnabled: true,
	snifferPorts: ['80', '443', '8080', '8443'],
	attackLogUploadInterval: 30
})

// 打开弹窗
const onOpen = (record) => {
	visible.value = true
	currentSafeId.value = record.id
	formData.value = defaultFormData()

	// 加载已有配置
	ewmProjectSafeApi.getConfig({ safeId: record.id }).then((res) => {
		if (res) {
			// 回显数据
			if (res.ipBlockerEnabled !== null && res.ipBlockerEnabled !== undefined) {
				formData.value.ipBlockerEnabled = res.ipBlockerEnabled
			}
			if (res.ipWhitelist) {
				try {
					formData.value.ipWhitelist = JSON.parse(res.ipWhitelist)
				} catch (e) {
					formData.value.ipWhitelist = []
				}
			}
			if (res.webLogSources) {
				try {
					formData.value.webLogSources = JSON.parse(res.webLogSources)
				} catch (e) {
					formData.value.webLogSources = []
				}
			}
			if (res.snifferPorts) {
				try {
					const ports = JSON.parse(res.snifferPorts)
					formData.value.snifferPorts = ports.map(String)
				} catch (e) {
					formData.value.snifferPorts = ['80', '443', '8080', '8443']
				}
			}
			if (res.snifferEnabled !== null && res.snifferEnabled !== undefined) {
				formData.value.snifferEnabled = res.snifferEnabled
			}
			if (res.attackLogUploadInterval !== null && res.attackLogUploadInterval !== undefined) {
				formData.value.attackLogUploadInterval = res.attackLogUploadInterval
			}
		}
	})
}

// 关闭弹窗
const onClose = () => {
	visible.value = false
}

// 添加Web日志源
const addWebLogSource = () => {
	formData.value.webLogSources.push({ path: '', type: 'nginx', enabled: true })
}

// 删除Web日志源
const removeWebLogSource = (index) => {
	formData.value.webLogSources.splice(index, 1)
}

// 保存配置
const onSubmit = () => {
	submitLoading.value = true
	const params = {
		safeId: currentSafeId.value,
		ipBlockerEnabled: formData.value.ipBlockerEnabled,
		ipWhitelist: formData.value.ipWhitelist,
		webLogSources: formData.value.webLogSources.filter(item => item.path),
		snifferPorts: formData.value.snifferPorts.map(Number).filter(n => !isNaN(n) && n > 0),
		snifferEnabled: formData.value.snifferEnabled,
		attackLogUploadInterval: formData.value.attackLogUploadInterval
	}
	ewmProjectSafeApi
		.saveConfig(params)
		.then(() => {
			message.success('配置保存成功')
		})
		.finally(() => {
			submitLoading.value = false
		})
}

// 下载配置JSON
const onDownload = () => {
	downloadLoading.value = true
	const token = localStorage.getItem('TOKEN') || ''
	const url = sysConfig.API_URL + '/safe/projectsafe/config/download?safeId=' + currentSafeId.value + '&token=' + token
	// 通过隐藏iframe下载
	const iframe = document.createElement('iframe')
	iframe.style.display = 'none'
	iframe.src = url
	document.body.appendChild(iframe)
	setTimeout(() => {
		document.body.removeChild(iframe)
		downloadLoading.value = false
	}, 3000)
}

defineExpose({
	onOpen
})
</script>

<style scoped>
.dynamic-delete-button {
	cursor: pointer;
	position: relative;
	top: 4px;
	font-size: 20px;
	color: #999;
	transition: all 0.3s;
}
.dynamic-delete-button:hover {
	color: #ff4d4f;
}
.dynamic-add-button {
	cursor: pointer;
	position: relative;
	top: 4px;
	font-size: 20px;
	color: #1890ff;
}
.ml-2 {
	margin-left: 8px;
}
.mb-2 {
	margin-bottom: 8px;
}
.text-center {
	text-align: center;
}
.web-log-section {
	margin-bottom: 16px;
}
</style>
