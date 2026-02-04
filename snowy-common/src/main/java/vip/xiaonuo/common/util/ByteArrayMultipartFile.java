package vip.xiaonuo.common.util;

import org.springframework.web.multipart.MultipartFile;

import java.io.*;
import java.nio.file.Files;
import java.nio.file.Path;

/**
 * 字节数组文件转换工具类
 * <p>
 * 用于在后端业务逻辑中，将内存中的 byte[] 伪装成前端上传的 MultipartFile 对象。
 * 适配 Spring 5.1+ / Spring Boot 2.1+ 版本。
 * </p>
 */
public class ByteArrayMultipartFile implements MultipartFile {

    private final String name;
    private final String originalFilename;
    private final String contentType;
    private final byte[] content;

    public ByteArrayMultipartFile(String name, String originalFilename, String contentType, byte[] content) {
        this.name = name;
        this.originalFilename = originalFilename;
        this.contentType = contentType;
        this.content = content;
    }

    @Override
    public String getName() {
        return this.name;
    }

    @Override
    public String getOriginalFilename() {
        return this.originalFilename;
    }

    @Override
    public String getContentType() {
        return this.contentType;
    }

    @Override
    public boolean isEmpty() {
        return this.content == null || this.content.length == 0;
    }

    @Override
    public long getSize() {
        return this.content.length;
    }

    @Override
    public byte[] getBytes() throws IOException {
        return this.content;
    }

    @Override
    public InputStream getInputStream() throws IOException {
        return new ByteArrayInputStream(this.content);
    }

    // ----------------------------------------------------------------
    // 下面是解决报错的关键：必须同时实现 File 和 Path 两个版本的 transferTo
    // ----------------------------------------------------------------

    /**
     * 传统 IO 方式写入文件
     */
    @Override
    public void transferTo(File dest) throws IOException, IllegalStateException {
        try (FileOutputStream fos = new FileOutputStream(dest)) {
            fos.write(this.content);
        }
    }

    /**
     * Java NIO 方式写入文件 (Spring 5.1+ 新增接口)
     */
    @Override
    public void transferTo(Path dest) throws IOException, IllegalStateException {
        Files.write(dest, this.content);
    }
}
