package vip.xiaonuo.ewm.modular.project.repository;

import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;
import vip.xiaonuo.ewm.modular.project.entity.AttackPortScan;
import vip.xiaonuo.ewm.modular.project.entity.WebAttack;

@Repository
public interface WebAttackRepository extends MongoRepository<WebAttack, String> {
}
