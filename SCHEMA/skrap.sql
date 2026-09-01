CREATE TABLE `skrap` (
  id integer PRIMARY KEY,
  name varchar(64) NOT NULL,
  type varchar(16) NOT NULL,
  owner_id integer NOT NULL,
  last_updated integer NOT NULL,    -- epoch seconds
  content text,
  UNIQUE(name, owner_id),
  FOREIGN KEY(owner_id) REFERENCES plugin(id)
);
