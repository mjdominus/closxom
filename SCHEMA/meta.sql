CREATE TABLE `meta` (
  id integer PRIMARY KEY,
  skrap_id integer,
  k varchar(64) NOT NULL,
  v blob,
  owner_id integer NOT NULL,
  UNIQUE(skrap_id, k),
  FOREIGN KEY(skrap_id) REFERENCES skrap(id),
  FOREIGN KEY(owner_id) REFERENCES plugin(id)
);

