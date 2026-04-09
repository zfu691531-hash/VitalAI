-- 更新用户密码哈希
-- 密码: admin123, teacher123, student123

UPDATE `user` SET `password_hash` = '$2b$12$l92frWnKvJdEVUGqlQ0.qedXAcLDGLjlMXEpOAqN7wvTD/r6QRUVu' WHERE `username` = 'admin';
UPDATE `user` SET `password_hash` = '$2b$12$TRYZ/MNIPSFQ21OepdFaeuHlu6nm5cwy/IH3v3rRpvM/J9MtLgeTS' WHERE `username` = 'wang_math';
UPDATE `user` SET `password_hash` = '$2b$12$HIERugjIOA4iztc0/14ZGOG6TLUY1rKrBY2Vwko9vRf4iqCJM54wO' WHERE `username` = 'liu_chinese';
UPDATE `user` SET `password_hash` = '$2b$12$vsVCLLeunUILB8abuGZ1ROWWkrneL8FRSpe1r8MglKYHcKecPsgm.' WHERE `username` = 'chen_english';
UPDATE `user` SET `password_hash` = '$2b$12$KDspmzRE/axJbFOjHPzTQ.jtqnO/o2uW6dM1lT0v2Y6LuH.MKj8XS' WHERE `username` = 'stu_2024001';
UPDATE `user` SET `password_hash` = '$2b$12$PUUwimdzWyzy5kP0rGY3ie9vnJqiOMdZuZOqhogeQkPkBGsfNPL7.' WHERE `username` = 'stu_2024002';
UPDATE `user` SET `password_hash` = '$2b$12$RoA7f9kcIBAHYON6z56EGeX3Zy.4gcA83MtJxcWIYJB0qSmrbGkfK' WHERE `username` = 'stu_2024003';
UPDATE `user` SET `password_hash` = '$2b$12$Be3Kb3N7n3AwqL9sNDdADunjWUpBcaEOnktOYmrOTck79K4sJnQFO' WHERE `username` = 'stu_2024004';
UPDATE `user` SET `password_hash` = '$2b$12$whfDE8rWJ5P9ex.UlP19nuFuVE8Nm88qGIxIL5WvYXMU3.32wvity' WHERE `username` = 'stu_2024005';
