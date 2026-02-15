package vip.xiaonuo.ewm.modular.project.repository;

import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;
import vip.xiaonuo.ewm.modular.project.entity.SafeHardware;

@Repository
public interface SafeHardwareRepository extends MongoRepository<SafeHardware, String> {
}
