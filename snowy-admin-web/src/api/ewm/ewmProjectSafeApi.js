import { baseRequest } from '@/utils/request'

const request = (url, ...arg) => baseRequest(`/safe/projectsafe/` + url, ...arg)
const wsRequest = (url, ...arg) => baseRequest(`/safe/ws/command/` + url, ...arg)

/**
 * 网络安全的客户端Api接口管理器
 *
 * @author Richai
 * @date  2026/02/15 23:15
 **/
export default {
	// 获取网络安全的客户端分页
	ewmProjectSafePage(data) {
		return request('page', data, 'get')
	},

	// 获取硬件监控数据
	monitor(data) {
		return request('monitor', data, 'get')
	},

	// 终端安全配置
	getConfig(data) {
		return request('config/detail', data, 'get')
	},
	saveConfig(data) {
		return request('config/save', data)
	},

	// WSS 指令下发
	sendAutoBlock(data) {
		return wsRequest('autoblock', data)
	},
	sendBlockIp(data) {
		return wsRequest('blockip', data)
	},
	sendWhitelist(data) {
		return wsRequest('whitelist', data)
	},
	sendShutdown(data) {
		return wsRequest('shutdown', data)
	}
}
