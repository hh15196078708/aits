import { baseRequest } from '@/utils/request'

const request = (url, ...arg) => baseRequest(`/ewm/project/` + url, ...arg)

/**
 * 项目表Api接口管理器
 *
 * @author Richai
 * @date  2025/12/24 16:30
 **/
export default {
	// 获取项目表分页
	ewmProjectPage(data) {
		return request('page', data, 'get')
	},
	// 提交项目表表单 edit为true时为编辑，默认为新增
	ewmProjectSubmitForm(data, edit = false) {
		return request(edit ? 'edit' : 'add', data)
	},
	// 删除项目表
	ewmProjectDelete(data) {
		return request('delete', data)
	},
	// 获取项目表详情
	ewmProjectDetail(data) {
		return request('detail', data, 'get')
	},
	// 下载项目表导入模板
	ewmProjectDownloadTemplate(data) {
		return request('downloadImportTemplate', data, 'get', {
			responseType: 'blob'
		})
	},
	// 导入项目表
	ewmProjectImport(data) {
		return request('importData', data)
	},
	// 导出项目表
	ewmProjectExport(data) {
		return request('exportData', data, 'post', {
			responseType: 'blob'
		})
	}
}
