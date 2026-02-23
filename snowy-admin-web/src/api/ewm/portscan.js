import { baseRequest } from '@/utils/request'

const request = (url, ...arg) => baseRequest(`/safe/portscan/` + url, ...arg)

/**
 * 网络安全的客户端Api接口管理器
 *
 * @author Richai
 * @date  2026/02/15 23:15
 **/
export default {
	// 获取网络安全的客户端分页
	attackPortScanPage(data) {
		return request('page', data, 'get')
	},

	// 获取硬件监控数据 (新增)
	attackPortScanDelete(data) {
		return request('delete', data)
	},
}
